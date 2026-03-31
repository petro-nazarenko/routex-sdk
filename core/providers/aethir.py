"""Aethir provider adapter — highest strategic priority for RouteX."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from core.types import ComputeProvider, JobRequest, JobStatus, ProviderQuote
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)

AETHIR_API_BASE = "https://api.aethir.com/v1"


class AethirProvider(BaseProvider):
    """
    Aethir enterprise GPU network.
    Aethir has ~1.4B compute hours delivered and $40M quarterly revenue (2025).
    Highest reliability score among supported providers.
    API keys obtained via aethir.com/ecosystem-fund (free for ecosystem partners).
    """

    def __init__(self, api_key: str, client_id: str) -> None:
        self._api_key  = api_key
        self._client_id = client_id
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> ComputeProvider:
        return ComputeProvider.AETHIR

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "x-api-key":   self._api_key,
                    "x-client-id": self._client_id,
                }
            )
        return self._session

    async def quote(self, job: JobRequest) -> Optional[ProviderQuote]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{AETHIR_API_BASE}/inference/quote",
                json={
                    "model":    job.model,
                    "vram_gb":  job.gpu_vram_gb,
                    "timeout":  job.timeout_s,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            if not data.get("available"):
                return None

            price_usd = data.get("estimated_cost_usd", 0)
            if price_usd > job.max_price_usd:
                return None

            return ProviderQuote(
                provider=self.name,
                price_usd=round(price_usd, 6),
                estimated_latency_ms=data.get("queue_ms", 2000),
                available=True,
                endpoint=AETHIR_API_BASE,
                # Aethir has highest reliability among DePIN compute (enterprise SLA)
                reliability_score=data.get("sla_uptime", 0.995),
                raw_response=data,
            )
        except Exception as exc:
            logger.debug("Aethir quote failed: %s", exc)
            return None

    async def submit(self, job: JobRequest, quote: ProviderQuote) -> str:
        session = await self._get_session()
        async with session.post(
            f"{AETHIR_API_BASE}/inference/jobs",
            json={
                "model":  job.model,
                "input":  job.input_data,
                "config": {"vram_gb": job.gpu_vram_gb, "timeout": job.timeout_s},
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["job_id"]

    async def poll_status(self, job_id: str) -> tuple[JobStatus, Optional[dict]]:
        session = await self._get_session()
        async with session.get(
            f"{AETHIR_API_BASE}/inference/jobs/{job_id}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        # Aethir job states
        status_map = {
            "queued":    JobStatus.PENDING,
            "running":   JobStatus.RUNNING,
            "success":   JobStatus.COMPLETED,
            "error":     JobStatus.FAILED,
            "cancelled": JobStatus.FAILED,
        }
        status = status_map.get(data.get("state", ""), JobStatus.PENDING)
        return status, data.get("output") if status == JobStatus.COMPLETED else None
