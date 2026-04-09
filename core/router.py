"""
RouteXRouter — core routing engine.

Algorithm:
  1. Gather quotes from all providers in parallel (with timeout)
  2. Score each quote: price (40%) + latency (40%) + reliability (20%)
  3. Filter by hard constraints: max_price_usd, max_latency_ms
  4. Select winner; dispatch job to winning provider
  5. Poll for completion
  6. Call settlement.settle() with job price and job_id

If preferred_provider is set in JobRequest, skips scoring and routes directly.
"""
from __future__ import annotations

import asyncio
import logging
import time

from core.providers.base import BaseProvider
from core.settlement import OnChainSettlement
from core.types import JobRequest, JobResult, JobStatus, ProviderQuote, RoutingDecision

logger = logging.getLogger(__name__)

# Weights must sum to 1.0
WEIGHT_PRICE       = 0.40
WEIGHT_LATENCY     = 0.40
WEIGHT_RELIABILITY = 0.20

# Timeout for collecting quotes from all providers (ms → seconds)
QUOTE_TIMEOUT_S = 5.0


class NoProviderAvailableError(Exception):
    pass


class RouteXRouter:
    """
    Main entry point for AI agents and developers.

    Usage:
        router = RouteXRouter(providers=[...], settlement=settlement)
        result = await router.route(job_request)
    """

    def __init__(
        self,
        providers: list[BaseProvider],
        settlement: OnChainSettlement,
    ) -> None:
        if not providers:
            raise ValueError("At least one provider required")
        self._providers  = {p.name: p for p in providers}
        self._settlement = settlement

    async def route(self, job: JobRequest) -> JobResult:
        """
        Full pipeline: quote → select → dispatch → poll → settle.
        Returns JobResult with settlement_tx populated on success.
        """
        t_start = time.monotonic()

        # ── 1. Direct routing (skip scoring) ─────────────────────────────────
        if job.preferred_provider:
            provider = self._providers.get(job.preferred_provider)
            if not provider:
                raise ValueError(f"Provider not registered: {job.preferred_provider}")
            quote = await provider.quote(job)
            if not quote or not quote.available:
                raise NoProviderAvailableError(
                    f"Preferred provider {job.preferred_provider} unavailable"
                )
            decision = RoutingDecision(
                winner=quote,
                all_quotes=[quote],
                routing_fee_usd=quote.price_usd * 0.01,
                score_breakdown={"direct": True},
            )
        else:
            # ── 2. Gather quotes in parallel ──────────────────────────────────
            decision = await self._select_provider(job)

        winner   = decision.winner
        provider = self._providers[winner.provider]

        logger.info(
            "Routing job to %s | price=$%.4f | latency=%dms",
            winner.provider.value,
            winner.price_usd,
            winner.estimated_latency_ms,
        )

        # ── 3. Submit ─────────────────────────────────────────────────────────
        job_id = await provider.submit(job, winner)
        logger.debug("Submitted job_id=%s to %s", job_id, winner.provider.value)

        # ── 4. Poll for completion ────────────────────────────────────────────
        status, output = await provider.wait_for_completion(
            job_id, timeout_s=job.timeout_s
        )

        latency_ms = int((time.monotonic() - t_start) * 1000)

        if status != JobStatus.COMPLETED:
            return JobResult(
                job_id=job_id,
                provider=winner.provider,
                status=status,
                output=None,
                price_paid_usd=winner.price_usd,
                latency_ms=latency_ms,
            )

        # ── 5. Settlement ─────────────────────────────────────────────────────
        tx_hash = await self._settlement.settle(winner.price_usd, job_id)

        logger.info(
            "Job %s completed | latency=%dms | tx=%s",
            job_id, latency_ms, tx_hash,
        )

        return JobResult(
            job_id=job_id,
            provider=winner.provider,
            status=JobStatus.COMPLETED,
            output=output,
            price_paid_usd=winner.price_usd,
            latency_ms=latency_ms,
            settlement_tx=tx_hash,
        )

    # ── Routing algorithm ─────────────────────────────────────────────────────

    async def _select_provider(self, job: JobRequest) -> RoutingDecision:
        quotes = await self._gather_quotes(job)

        eligible = [
            q for q in quotes
            if q.available
            and q.price_usd     <= job.max_price_usd
            and q.estimated_latency_ms <= job.max_latency_ms
        ]

        if not eligible:
            providers_tried = [q.provider.value for q in quotes]
            raise NoProviderAvailableError(
                f"No provider met constraints (price<=${job.max_price_usd}, "
                f"latency<={job.max_latency_ms}ms). Tried: {providers_tried}"
            )

        scored = [(self._score(q, eligible), q) for q in eligible]
        scored.sort(key=lambda x: x[0], reverse=True)

        winner    = scored[0][1]
        fee_usd   = winner.price_usd * 0.01

        return RoutingDecision(
            winner=winner,
            all_quotes=quotes,
            routing_fee_usd=fee_usd,
            score_breakdown={q.provider.value: round(s, 4) for s, q in scored},
        )

    async def _gather_quotes(self, job: JobRequest) -> list[ProviderQuote]:
        """Query all registered providers in parallel. Silently drops timeouts."""
        tasks = {
            name: asyncio.create_task(provider.quote(job))
            for name, provider in self._providers.items()
        }
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True),
                timeout=QUOTE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning("Quote collection timed out after %.1fs", QUOTE_TIMEOUT_S)
            results = [t.result() if not t.cancelled() and not t.exception() else None
                       for t in tasks.values()]

        quotes = []
        for result in results:
            if isinstance(result, ProviderQuote) and result is not None:
                quotes.append(result)
            elif result is None or isinstance(result, Exception):
                pass  # unavailable provider — silently skipped

        return quotes

    @staticmethod
    def _score(quote: ProviderQuote, eligible: list[ProviderQuote]) -> float:
        """
        Normalised score in [0, 1]. Higher = better.
        Price:     lower is better  → invert (max_price - price) / range
        Latency:   lower is better  → same inversion
        Reliability: higher is better → direct
        """
        prices    = [q.price_usd              for q in eligible]
        latencies = [q.estimated_latency_ms   for q in eligible]

        def normalise_inv(val, vals):
            lo, hi = min(vals), max(vals)
            return (hi - val) / (hi - lo) if hi != lo else 1.0

        def normalise(val, vals):
            lo, hi = min(vals), max(vals)
            return (val - lo) / (hi - lo) if hi != lo else 1.0

        score = (
            WEIGHT_PRICE       * normalise_inv(quote.price_usd, prices)
            + WEIGHT_LATENCY   * normalise_inv(quote.estimated_latency_ms, latencies)
            + WEIGHT_RELIABILITY * normalise(quote.reliability_score, [q.reliability_score for q in eligible])
        )
        return score
