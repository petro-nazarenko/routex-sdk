"""Nosana provider adapter (Solana-native, REST API)."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from core.providers.base import BaseProvider
from core.types import ComputeProvider, JobRequest, JobStatus, ProviderQuote

logger = logging.getLogger(__name__)

NOSANA_API_BASE = "https://api.nosana.io/v1"


class NosanaProvider(BaseProvider):
    """
    Nosana GPU marketplace (Solana-native but exposes a REST API usable cross-chain).
    Payment is bridged via cross-chain settlement — RouteX pays in the protocol token,
    settlement contract handles NOS conversion off-chain.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> ComputeProvider:
        return ComputeProvider.NOSANA

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"x-api-key": self._api_key}
            )
        return self._session

    async def quote(self, job: JobRequest) -> Optional[ProviderQuote]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{NOSANA_API_BASE}/markets",
                params={"min_vram": job.gpu_vram_gb},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                markets = await resp.json()

            if not markets:
                return None

            # Nosana pricing: job_timeout × price_per_second
            best = min(markets, key=lambda m: m.get("price_usd_per_second", 9))
            price_usd = best["price_usd_per_second"] * job.timeout_s
            if price_usd > job.max_price_usd:
                return None

            return ProviderQuote(
                provider=self.name,
                price_usd=round(price_usd, 6),
                estimated_latency_ms=best.get("avg_queue_ms", 5000),
                available=True,
                endpoint=best.get("endpoint", NOSANA_API_BASE),
                reliability_score=best.get("uptime", 0.92),
                raw_response=best,
            )
        except Exception as exc:
            logger.debug("Nosana quote failed: %s", exc)
            return None

    async def submit(self, job: JobRequest, quote: ProviderQuote) -> str:
        session = await self._get_session()
        async with session.post(
            f"{NOSANA_API_BASE}/jobs",
            json={"model": job.model, "input": job.input_data},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["job_id"]

    async def poll_status(self, job_id: str) -> tuple[JobStatus, Optional[dict]]:
        session = await self._get_session()
        async with session.get(
            f"{NOSANA_API_BASE}/jobs/{job_id}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        status_map = {"queued": JobStatus.PENDING, "running": JobStatus.RUNNING,
                      "completed": JobStatus.COMPLETED, "failed": JobStatus.FAILED}
        status = status_map.get(data.get("status", ""), JobStatus.PENDING)
        return status, data.get("result") if status == JobStatus.COMPLETED else None
