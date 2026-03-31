# RouteX SDK — Compute Routing Aggregator for AI Agents

**Grant Tier:** Seed — $1,000
**Applicant:** petro-nazarenko
**Repository:** https://github.com/petro-nazarenko/routex-sdk
**Category:** Developer Tooling / AI Infrastructure

---

## Problem

250,000+ AI agents run on-chain daily (Q1 2026). Each needs GPU compute on demand.

The problem: Akash, Nosana, io.net, and Aethir are isolated ecosystems. An agent that wants to find the cheapest H100 for inference must integrate 4 different APIs, handle 4 different payment tokens, and manage 4 different job lifecycle flows.

This fragmentation means agents either hardcode a single provider (overpaying) or developers spend weeks building custom routing logic for every project.

The same problem existed for DEX liquidity — until 1inch solved it with a routing layer. RouteX is that routing layer for GPU compute.

---

## Solution

RouteX SDK is an open-source Python library that gives AI agents a single interface to route GPU jobs across decentralized compute networks — including Akash.

```python
from core.router import RouteXRouter
from core.types import JobRequest

router = RouteXRouter(providers=[akash, nosana, ionet, aethir], settlement=settlement)
result = await router.route(JobRequest(
    model="meta-llama/Llama-3-70b",
    max_price_usd=0.10,
    max_latency_ms=5000
))
# RouteX quotes all providers in parallel (5s timeout)
# Selects winner by price(40%) + latency(40%) + reliability(20%)
# Submits job, polls status, returns result
```

One call. Best price. No provider lock-in.

---

## Current State

The SDK is functional with the following components:

- **Core routing engine** — parallel quote collection with 5s timeout, normalised scoring algorithm, job dispatch and status polling
- **Provider adapters** — Akash, Nosana, io.net, Aethir. Currently using test stubs; live Akash API integration is the primary deliverable of this grant
- **CLI interface:**

```bash
# Get quotes from all providers
python -m cli quote --model "meta-llama/Llama-3-70b" --vram 24

# Route a job (dry run)
DRY_RUN=true python -m cli route --model "meta-llama/Llama-3-70b"
```

- **Test suite** — 10 unit tests covering routing logic, provider failures, fallback behavior, hard-constraint filtering, and score normalisation. All providers mocked for CI.

---

## Milestones

### Milestone 1 — Working CLI Demo *(2 weeks)*

**Deliverable:** Public screen recording showing RouteX CLI routing a real inference job across at least 2 providers (Akash included), with actual quotes and job completion.

- Integrate live Akash API (SDL deployment, lease creation, job polling) replacing test stubs
- Publish demo video + step-by-step guide on how to run locally
- Add Akash deployment example to `/examples/akash_inference.py`

### Milestone 2 — Verified Akash Job End-to-End *(2 weeks after M1)*

**Deliverable:** Verified on-chain Akash deployment submitted via RouteX SDK, documented with transaction hash and Akash Console link.

- Deploy Llama-3 inference container on Akash Testnet via SDK
- Document SDL template generation from `JobRequest` schema
- Publish integration guide on Akash forum

---

## Why Akash Benefits

Every RouteX user is a potential Akash customer. When Akash wins the routing competition on price/latency, the job goes to Akash automatically — no extra steps for the developer.

AI agent developers don't want to learn Akash SDL. RouteX abstracts that entirely. Lower barrier = more deployments.

Akash's BME model (burn AKT → mint ACT) makes Akash more price-competitive at scale. RouteX will surface that advantage to agents automatically — without requiring agents to hold AKT.

---

## Open Source Commitment

- Repository is and will remain MIT licensed
- All provider adapters documented for community contribution
- Guide published on Akash forum after each milestone
- No token dependency — RouteX SDK works with any settlement layer; no $ROUTE token required

---

## About the Developer

Solo developer building open-source AI infrastructure tooling. Currently maintaining two projects:

- **RouteX SDK** — compute routing for AI agents *(this proposal)*
- **K-Fleet MVP** — MARPOL compliance automation for vessel logbooks

Primary stack: Python, asyncio, FastAPI. Development environment: Hetzner VPS + Termux.
GitHub: https://github.com/petro-nazarenko

---

## Budget

$1,000 allocated as follows:

| Item | Amount |
|------|--------|
| Akash Testnet compute (deployment testing, job runs) | ~$600 |
| Real inference jobs to validate routing vs. live provider pricing | ~$250 |
| Forum guides, documentation, community support time | ~$150 |
