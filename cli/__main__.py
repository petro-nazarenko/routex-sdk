"""
RouteX SDK CLI — for testing routing without writing code.

Usage:
  python -m cli route --model "meta-llama/Llama-3-70b" --input '{"prompt":"hi"}' --dry-run
  python -m cli quote --model "meta-llama/Llama-3-70b"
  python -m cli providers
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.providers.akash   import AkashProvider
from core.providers.aethir  import AethirProvider
from core.providers.nosana  import NosanaProvider
from core.providers.ionet   import IoNetProvider
from core.router     import RouteXRouter
from core.settlement import OnChainSettlement
from core.types      import JobRequest, ComputeProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cli")


def _build_providers() -> list:
    providers = []

    if os.environ.get("AKASH_API_KEY"):
        providers.append(AkashProvider(
            api_key=os.environ["AKASH_API_KEY"],
            wallet_address=os.environ.get("AKASH_WALLET", ""),
        ))

    if os.environ.get("NOSANA_API_KEY"):
        providers.append(NosanaProvider(api_key=os.environ["NOSANA_API_KEY"]))

    if os.environ.get("IONET_API_KEY"):
        providers.append(IoNetProvider(api_key=os.environ["IONET_API_KEY"]))

    if os.environ.get("AETHIR_API_KEY"):
        providers.append(AethirProvider(
            api_key=os.environ["AETHIR_API_KEY"],
            client_id=os.environ.get("AETHIR_CLIENT_ID", ""),
        ))

    if not providers:
        logger.error(
            "No providers configured. Set at least one of: "
            "AKASH_API_KEY, NOSANA_API_KEY, IONET_API_KEY, AETHIR_API_KEY"
        )
        sys.exit(1)

    return providers


async def cmd_providers(args) -> None:
    """List configured providers and their availability."""
    providers = _build_providers()
    job = JobRequest(model="test", input_data={}, gpu_vram_gb=8, max_price_usd=10.0)

    print("\nConfigured providers:")
    for p in providers:
        quote = await p.quote(job)
        status = f"✅ ${quote.price_usd:.4f}  {quote.estimated_latency_ms}ms" if quote else "❌ unavailable"
        print(f"  {p.name.value:<12} {status}")
    print()


async def cmd_quote(args) -> None:
    """Get quotes from all providers for a given job spec."""
    providers = _build_providers()
    job = JobRequest(
        model=args.model,
        input_data=json.loads(args.input) if args.input else {},
        gpu_vram_gb=args.vram,
        max_price_usd=args.max_price,
    )

    print(f"\nQuotes for model={job.model} vram={job.gpu_vram_gb}GB:")
    for p in providers:
        quote = await p.quote(job)
        if quote:
            print(
                f"  {quote.provider.value:<12} "
                f"${quote.price_usd:.6f}  "
                f"{quote.estimated_latency_ms}ms  "
                f"reliability={quote.reliability_score:.2f}"
            )
        else:
            print(f"  {p.name.value:<12} unavailable")
    print()


async def cmd_route(args) -> None:
    """Route a job and optionally settle on-chain."""
    dry_run = args.dry_run or os.environ.get("DRY_RUN", "false").lower() == "true"

    providers = _build_providers()
    settlement = OnChainSettlement(dry_run=dry_run)

    preferred = None
    if args.provider:
        try:
            preferred = ComputeProvider(args.provider)
        except ValueError:
            logger.error("Unknown provider: %s", args.provider)
            sys.exit(1)

    job = JobRequest(
        model=args.model,
        input_data=json.loads(args.input) if args.input else {"prompt": "test"},
        gpu_vram_gb=args.vram,
        max_price_usd=args.max_price,
        preferred_provider=preferred,
    )

    router = RouteXRouter(providers=providers, settlement=settlement)

    if dry_run:
        logger.info("[DRY_RUN] Will route job but skip on-chain settlement")

    result = await router.route(job)

    print(f"\n{'='*50}")
    print(f"Job ID:      {result.job_id}")
    print(f"Provider:    {result.provider.value}")
    print(f"Status:      {result.status.value}")
    print(f"Latency:     {result.latency_ms}ms")
    print(f"Price paid:  ${result.price_paid_usd:.6f}")
    if result.settlement_tx:
        print(f"Settlement:  {result.settlement_tx}")
    if result.output:
        print(f"Output:      {json.dumps(result.output, indent=2)[:500]}")
    print(f"{'='*50}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="RouteX SDK CLI")
    sub    = parser.add_subparsers(dest="command")

    # providers
    sub.add_parser("providers", help="List configured providers")

    # quote
    q = sub.add_parser("quote", help="Get price quotes without routing")
    q.add_argument("--model",     required=True)
    q.add_argument("--input",     default=None)
    q.add_argument("--vram",      type=int, default=24)
    q.add_argument("--max-price", type=float, default=1.0, dest="max_price")

    # route
    r = sub.add_parser("route", help="Route a job and settle on-chain")
    r.add_argument("--model",     required=True)
    r.add_argument("--input",     default=None)
    r.add_argument("--vram",      type=int, default=24)
    r.add_argument("--max-price", type=float, default=1.0, dest="max_price")
    r.add_argument("--provider",  default=None, help="Pin to specific provider")
    r.add_argument("--dry-run",   action="store_true", help="Skip on-chain settlement")

    args = parser.parse_args()

    cmd_map = {
        "providers": cmd_providers,
        "quote":     cmd_quote,
        "route":     cmd_route,
    }

    if args.command not in cmd_map:
        parser.print_help()
        sys.exit(0)

    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
