"""
Router unit tests — all provider calls are mocked.

Run: pytest tests/test_router.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.router import NoProviderAvailableError, RouteXRouter
from core.types import ComputeProvider, JobRequest, JobStatus, ProviderQuote

# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_job(
    model: str = "meta-llama/Llama-3-70b",
    input_data: dict | None = None,
    gpu_vram_gb: int = 24,
    max_price_usd: float = 1.0,
    max_latency_ms: int = 30_000,
    timeout_s: int = 60,
    preferred_provider: ComputeProvider | None = None,
) -> JobRequest:
    return JobRequest(
        model=model,
        input_data=input_data if input_data is not None else {"prompt": "hello"},
        gpu_vram_gb=gpu_vram_gb,
        max_price_usd=max_price_usd,
        max_latency_ms=max_latency_ms,
        timeout_s=timeout_s,
        preferred_provider=preferred_provider,
    )


def make_quote(
    provider=ComputeProvider.AKASH,
    price=0.05,
    latency=5000,
    reliability=0.95,
    available=True,
) -> ProviderQuote:
    return ProviderQuote(
        provider=provider,
        price_usd=price,
        estimated_latency_ms=latency,
        available=available,
        endpoint="https://fake.api",
        reliability_score=reliability,
    )


def make_provider(quote: ProviderQuote | None, job_id="job-123") -> MagicMock:
    p = MagicMock()
    p.name = quote.provider if quote else ComputeProvider.AKASH
    p.quote = AsyncMock(return_value=quote)
    p.submit = AsyncMock(return_value=job_id)
    p.wait_for_completion = AsyncMock(return_value=(JobStatus.COMPLETED, {"result": "ok"}))
    return p


def make_settlement(tx="0xabc") -> MagicMock:
    s = MagicMock()
    s.settle = AsyncMock(return_value=tx)
    return s


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_route_selects_cheapest_provider():
    """Router picks the cheapest eligible provider."""
    cheap  = make_quote(ComputeProvider.AKASH,  price=0.02, latency=5000)
    pricey = make_quote(ComputeProvider.AETHIR, price=0.08, latency=2000)

    p_cheap  = make_provider(cheap,  "job-cheap")
    p_pricey = make_provider(pricey, "job-pricey")

    router = RouteXRouter(
        providers=[p_cheap, p_pricey],
        settlement=make_settlement(),
    )
    result = await router.route(make_job())

    assert result.provider == ComputeProvider.AKASH
    assert result.status   == JobStatus.COMPLETED
    assert result.settlement_tx == "0xabc"


@pytest.mark.asyncio
async def test_route_all_providers_unavailable_raises():
    p1 = make_provider(None)
    p2 = make_provider(make_quote(available=False))

    router = RouteXRouter(providers=[p1, p2], settlement=make_settlement())

    with pytest.raises(NoProviderAvailableError):
        await router.route(make_job())


@pytest.mark.asyncio
async def test_route_skips_provider_exceeding_max_price():
    expensive = make_quote(ComputeProvider.AETHIR, price=5.0)  # > max_price_usd=1.0
    cheap     = make_quote(ComputeProvider.AKASH,  price=0.05)

    p_exp   = make_provider(expensive)
    p_cheap = make_provider(cheap, "job-ok")

    router = RouteXRouter(providers=[p_exp, p_cheap], settlement=make_settlement())
    result = await router.route(make_job(max_price_usd=1.0))

    assert result.provider == ComputeProvider.AKASH


@pytest.mark.asyncio
async def test_route_skips_provider_exceeding_latency():
    slow = make_quote(ComputeProvider.NOSANA, latency=60_000)  # > max_latency_ms=30k
    fast = make_quote(ComputeProvider.AKASH,  latency=4_000)

    router = RouteXRouter(
        providers=[make_provider(slow), make_provider(fast, "job-fast")],
        settlement=make_settlement(),
    )
    result = await router.route(make_job(max_latency_ms=30_000))

    assert result.provider == ComputeProvider.AKASH


@pytest.mark.asyncio
async def test_route_preferred_provider_skips_scoring():
    aethir_quote = make_quote(ComputeProvider.AETHIR, price=0.99)
    akash_quote  = make_quote(ComputeProvider.AKASH,  price=0.01)

    p_aethir = make_provider(aethir_quote, "job-aethir")
    p_akash  = make_provider(akash_quote,  "job-akash")

    router = RouteXRouter(providers=[p_aethir, p_akash], settlement=make_settlement())

    # Force Aethir even though it's more expensive
    result = await router.route(
        make_job(preferred_provider=ComputeProvider.AETHIR)
    )
    assert result.provider == ComputeProvider.AETHIR
    p_aethir.quote.assert_called_once()
    p_akash.quote.assert_not_called()   # scoring bypassed


@pytest.mark.asyncio
async def test_route_preferred_provider_unavailable_raises():
    p = make_provider(None)
    p.name = ComputeProvider.IONET

    router = RouteXRouter(providers=[p], settlement=make_settlement())

    with pytest.raises(NoProviderAvailableError):
        await router.route(make_job(preferred_provider=ComputeProvider.IONET))


@pytest.mark.asyncio
async def test_route_failed_job_no_settlement():
    """Settlement must NOT be called if job fails."""
    q = make_quote(ComputeProvider.AKASH)
    p = make_provider(q)
    p.wait_for_completion = AsyncMock(return_value=(JobStatus.FAILED, None))

    settlement = make_settlement()
    router = RouteXRouter(providers=[p], settlement=settlement)
    result = await router.route(make_job())

    assert result.status == JobStatus.FAILED
    assert result.settlement_tx is None
    settlement.settle.assert_not_called()


@pytest.mark.asyncio
async def test_route_settlement_called_with_correct_args():
    q = make_quote(ComputeProvider.AETHIR, price=0.10)  # $0.10 job
    p = make_provider(q)

    settlement = make_settlement()

    router = RouteXRouter(providers=[p], settlement=settlement)
    await router.route(make_job())

    # settle called with (job_price=0.10, job_id="job-123")
    settlement.settle.assert_called_once_with(0.10, "job-123")


@pytest.mark.asyncio
async def test_scoring_prefers_reliability_on_price_tie():
    """When prices are equal, higher reliability wins."""
    low_rel  = make_quote(ComputeProvider.AKASH,  price=0.05, reliability=0.80, latency=5000)
    high_rel = make_quote(ComputeProvider.AETHIR, price=0.05, reliability=0.99, latency=5000)

    router = RouteXRouter(
        providers=[make_provider(low_rel), make_provider(high_rel, "job-aethir")],
        settlement=make_settlement(),
    )
    result = await router.route(make_job())
    assert result.provider == ComputeProvider.AETHIR


def test_score_normalisation_single_provider():
    """With one provider, score should be 1.0 regardless of values."""
    q      = make_quote(price=999.0, latency=99_999, reliability=0.01)
    score  = RouteXRouter._score(q, [q])
    assert score == 1.0
