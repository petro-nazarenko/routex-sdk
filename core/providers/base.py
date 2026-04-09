"""Abstract provider interface. All compute network adapters implement this."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from core.types import ComputeProvider, JobRequest, JobStatus, ProviderQuote


class BaseProvider(ABC):
    """
    One instance per compute network (Akash, Nosana, io.net, Aethir).
    All methods are async — quote() and submit() may call external APIs.
    """

    @property
    @abstractmethod
    def name(self) -> ComputeProvider:
        ...

    @abstractmethod
    async def quote(self, job: JobRequest) -> Optional[ProviderQuote]:
        """
        Return a price quote for this job, or None if unavailable.
        Must not raise — return None on any error (router skips unavailable providers).
        """
        ...

    @abstractmethod
    async def submit(self, job: JobRequest, quote: ProviderQuote) -> str:
        """
        Submit the job. Returns a provider-specific job_id string.
        Raises on failure.
        """
        ...

    @abstractmethod
    async def poll_status(self, job_id: str) -> tuple[JobStatus, Optional[dict]]:
        """
        Check job status. Returns (status, output_or_None).
        Called repeatedly until status is terminal (COMPLETED / FAILED / TIMEOUT).
        """
        ...

    async def wait_for_completion(
        self,
        job_id: str,
        timeout_s: int = 300,
        poll_interval_s: float = 2.0,
    ) -> tuple[JobStatus, Optional[dict]]:
        """Poll until terminal status or timeout."""
        elapsed = 0.0
        while elapsed < timeout_s:
            status, output = await self.poll_status(job_id)
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT):
                return status, output
            await asyncio.sleep(poll_interval_s)
            elapsed += poll_interval_s
        return JobStatus.TIMEOUT, None
