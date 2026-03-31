"""Akash Network provider adapter."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from core.types import ComputeProvider, JobRequest, JobResult, JobStatus, ProviderQuote
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Akash REST API base (SDL deployments via REST proxy or custom indexer)
# In production: replace with your Akash deployment manager endpoint
AKASH_API_BASE = "https://api.akash.network/v1"


class AkashProvider(BaseProvider):
    """
    Akash Network adapter.
    Akash uses SDL (deployment manifests) — we abstract this to a simple
    model-name → SDL template mapping.
    Pricing is in AKT but we convert to USD via CoinGecko at quote time.
    """

    def __init__(self, api_key: str, wallet_address: str) -> None:
        self._api_key = api_key
        self._wallet  = wallet_address
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> ComputeProvider:
        return ComputeProvider.AKASH

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        return self._session

    async def quote(self, job: JobRequest) -> Optional[ProviderQuote]:
        try:
            session = await self._get_session()
            # Query available GPU providers that match vRAM requirement
            async with session.get(
                f"{AKASH_API_BASE}/providers",
                params={"gpu_vram_min": job.gpu_vram_gb, "available": True},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            providers = data.get("providers", [])
            if not providers:
                return None

            # Pick cheapest available provider
            best = min(providers, key=lambda p: p.get("price_usd_per_hour", 999))
            # Estimate cost: assume 5-minute average job
            price_usd = best.get("price_usd_per_hour", 0.5) * (5 / 60)
            if price_usd > job.max_price_usd:
                return None

            return ProviderQuote(
                provider=self.name,
                price_usd=round(price_usd, 6),
                estimated_latency_ms=best.get("avg_latency_ms", 8000),
                available=True,
                endpoint=best.get("endpoint", AKASH_API_BASE),
                reliability_score=best.get("uptime_30d", 0.95),
                raw_response=best,
            )
        except Exception as exc:
            logger.debug("Akash quote failed: %s", exc)
            return None

    async def submit(self, job: JobRequest, quote: ProviderQuote) -> str:
        session = await self._get_session()
        payload = {
            "model":       job.model,
            "input":       job.input_data,
            "gpu_vram_gb": job.gpu_vram_gb,
            "wallet":      self._wallet,
        }
        async with session.post(
            f"{quote.endpoint}/deployments",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["deployment_id"]

    async def poll_status(self, job_id: str) -> tuple[JobStatus, Optional[dict]]:
        session = await self._get_session()
        async with session.get(
            f"{AKASH_API_BASE}/deployments/{job_id}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status == 404:
                return JobStatus.FAILED, None
            resp.raise_for_status()
            data = await resp.json()

        state_map = {
            "active":    JobStatus.RUNNING,
            "complete":  JobStatus.COMPLETED,
            "closed":    JobStatus.COMPLETED,
            "failed":    JobStatus.FAILED,
        }
        status = state_map.get(data.get("state", ""), JobStatus.PENDING)
        output = data.get("result") if status == JobStatus.COMPLETED else None
        return status, output
