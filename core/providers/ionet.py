"""io.net provider adapter."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from core.types import ComputeProvider, JobRequest, JobStatus, ProviderQuote
from core.providers.base import BaseProvider

logger = logging.getLogger(__name__)

IONET_API_BASE = "https://api.io.net/v1"


class IoNetProvider(BaseProvider):
    """
    io.net GPU cluster marketplace.
    Exposes cluster-based pricing — we map single-job requests to smallest cluster.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> ComputeProvider:
        return ComputeProvider.IONET

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        return self._session

    async def quote(self, job: JobRequest) -> Optional[ProviderQuote]:
        try:
            session = await self._get_session()
            async with session.post(
                f"{IONET_API_BASE}/quote",
                json={"gpu_vram": job.gpu_vram_gb, "duration_s": job.timeout_s},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            price_usd = data.get("total_price_usd", 0)
            if price_usd == 0 or price_usd > job.max_price_usd:
                return None

            return ProviderQuote(
                provider=self.name,
                price_usd=round(price_usd, 6),
                estimated_latency_ms=data.get("setup_latency_ms", 3000),
                available=data.get("available", False),
                endpoint=IONET_API_BASE,
                reliability_score=data.get("sla_uptime", 0.99),
                raw_response=data,
            )
        except Exception as exc:
            logger.debug("io.net quote failed: %s", exc)
            return None

    async def submit(self, job: JobRequest, quote: ProviderQuote) -> str:
        session = await self._get_session()
        async with session.post(
            f"{IONET_API_BASE}/jobs",
            json={"model": job.model, "input": job.input_data, "gpu_vram": job.gpu_vram_gb},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["id"]

    async def poll_status(self, job_id: str) -> tuple[JobStatus, Optional[dict]]:
        session = await self._get_session()
        async with session.get(
            f"{IONET_API_BASE}/jobs/{job_id}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        status_map = {"pending": JobStatus.PENDING, "running": JobStatus.RUNNING,
                      "done": JobStatus.COMPLETED, "error": JobStatus.FAILED}
        status = status_map.get(data.get("status", ""), JobStatus.PENDING)
        return status, data.get("output") if status == JobStatus.COMPLETED else None
