# routex-sdk

Python SDK for routing AI agent compute jobs across decentralized GPU networks — Aethir, io.net, Nosana, and Akash.

**One SDK call → parallel quotes → cheapest/fastest provider selected → job dispatched → result returned.**

---

## Problem

250,000+ AI agents run on-chain daily (Q1 2026). Each needs GPU compute. Five compute networks are walled gardens — agents can't route atomically across them. This SDK is the routing layer.

## Solution

```
AI Agent
   │
   └─► RouteXRouter.route(job)
             │
             ├─ quote() ──► Aethir   $0.04  2s
             ├─ quote() ──► io.net   $0.06  3s   ← parallel, timeout 5s
             ├─ quote() ──► Nosana   $0.05  4s
             └─ quote() ──► Akash    $0.03  6s ✓ winner
                                │
                           submit + poll
                                │
                     settlement.settle()       ← pluggable hook
```

---

## Quick Start

```bash
pip install -r requirements.txt

# List configured providers
AKASH_API_KEY=xxx AETHIR_API_KEY=yyy python -m cli providers

# Get quotes (no job dispatch)
python -m cli quote --model "meta-llama/Llama-3-70b" --vram 24

# Route a job — dry run (no settlement)
DRY_RUN=true python -m cli route \
  --model "meta-llama/Llama-3-70b" \
  --input '{"prompt": "hello"}' \
  --dry-run

# Route a job — live
python -m cli route --model "meta-llama/Llama-3-70b"
```

**Provider env vars:**

| Variable | Provider |
|----------|----------|
| `AKASH_API_KEY` | Akash Network |
| `AKASH_WALLET` | Akash wallet address |
| `NOSANA_API_KEY` | Nosana |
| `IONET_API_KEY` | io.net |
| `AETHIR_API_KEY` | Aethir |
| `AETHIR_CLIENT_ID` | Aethir client ID |

---

## Tests

```bash
pytest tests/test_router.py -v
pytest tests/test_router.py -v -k "test_route_failed"
```

---

## Architecture

```
core/
├── router.py           RouteXRouter — quote, score, dispatch, settle
├── settlement.py       Pluggable settlement hook (stub — implement for your protocol)
├── types.py            JobRequest, ProviderQuote, JobResult
└── providers/          Akash · Nosana · io.net · Aethir adapters
    └── base.py         BaseProvider ABC

cli/
└── __main__.py         CLI for testing: providers / quote / route

tests/
└── test_router.py      Unit tests (all providers mocked)
```

### Routing algorithm

Score = `price×0.40 + latency×0.40 + reliability×0.20` (all normalised to [0,1]).

Hard constraints filtered first: `max_price_usd`, `max_latency_ms`. If `preferred_provider` is set, scoring is skipped.

### Settlement hook

`core/settlement.py` is a no-op stub. To add on-chain fee settlement:

```python
class OnChainSettlement:
    async def settle(self, job_price_usd: float, job_id: str) -> str | None:
        # your implementation here
        ...
```

For a full ERC-20 burn + staker distribution reference implementation, see the `routex-protocol` repository.

---

## Adding a provider

1. Create `core/providers/myprovider.py` implementing `BaseProvider` (quote / submit / poll_status)
2. Add `MyProvider` to `ComputeProvider` enum in `types.py`
3. Wire in `cli/__main__.py` via env var check
