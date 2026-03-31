# Pain Point — Problem Statement

> Phase 0.2 Output

---

## Selected Problem: No Unified Routing & Settlement Layer for AI Agent ↔ GPU Compute

### One-line statement
AI agents need GPU compute to run inference, but each DePIN compute network (Aethir, io.net, Nosana, Akash) is a walled garden — agents can't discover, compare, or pay across networks in a single atomic transaction.

---

## The Problem in Detail

### Context
In Q1 2026, 250,000+ AI agents operate on-chain daily. 68% of new DeFi protocols include at least one autonomous agent. These agents need compute to run LLM inference, execute ML models, or process data. The GPU compute market (DePIN) has $19B+ in tokenized value across 650+ active projects.

### The gap
Every compute provider operates its own token economy:
- **Aethir** → $ATH token, own marketplace
- **io.net** → $IO token, own API
- **Nosana** → $NOS token, Solana-native
- **Akash** → $AKT token, Cosmos-based

An AI agent that needs to route a job to the cheapest/fastest GPU must:
1. Hold multiple native tokens
2. Call each network's API separately
3. Handle different payment rails
4. No cross-network SLA guarantees or dispute resolution

This is the **"compute fragmentation" problem** — identical to how DeFi liquidity was fragmented before DEX aggregators (1inch, Paraswap). Those aggregators became multi-billion dollar protocols.

### Why no dominant solution exists
- Existing aggregators (Lilypad, Morpheus) focus on routing for human developers, not machine-to-machine (agent-to-agent) payments
- No protocol has native ERC-20 payment abstraction + atomic cross-network job dispatch
- Agent payment standards (ERC-8004, x402) just launched Feb 2026 — too new for existing routing protocols to have integrated
- Deep integration requires partnerships with 5+ compute networks simultaneously → coordination problem that takes time

### Evidence of real user demand
1. Aethir: $40M quarterly revenue (2025) — real fees, real demand
2. io.net + Nosana: $400M+ market caps — market validated
3. Virtual Protocol: $479M AI-driven economic activity via 23,500 agents (March 2026)
4. 68% of new DeFi Q1 2026 launches include AI agents needing compute
5. GPU supply constraints confirmed by Nvidia (demand > supply through fiscal 2026)

---

## Target User

**Primary:** On-chain AI agents (autonomous programs) that need to purchase compute at runtime
**Secondary:** AI agent developers who want their agents to source compute cost-efficiently
**Tertiary:** DePIN compute providers who want demand routed to their idle capacity

User size: 250,000+ active agents today, projected to grow 10× by 2027 per market trajectory.

---

## Why Now

| Factor | Detail |
|--------|--------|
| Supply shock | Nvidia Vera Rubin era: GPU demand > supply confirmed |
| Standard adoption | ERC-8004 (agent identity) + x402 (agent payments) just live |
| Market validation | $40M/quarter real revenue in compute sector |
| Infrastructure ready | Base + Arbitrum can handle high-frequency micro-settlements cheaply |
| No dominant aggregator | 0 protocols with >$100M TVL in cross-network compute routing |

---

## Token-Incentivized Solution

**Protocol:** Compute Router — an on-chain aggregator that:
1. Queries Aethir / io.net / Nosana / Akash APIs for best price/latency
2. Converts agent payment (single token) to native network tokens atomically
3. Settles jobs on-chain, records proofs
4. Burns % of routing fees → deflationary pressure

**Token role:**
- Payment unit for routing fee
- Staking by compute providers to be listed (skin in game)
- Governance over supported networks and fee parameters
- Buy & burn from routing volume = direct revenue → deflation link

**Comparable:** 1inch (DEX aggregation) but for GPU compute, with native AI agent payment rail.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Compute networks block integration | Start with open APIs (Akash, Nosana); Aethir/io.net have public endpoints |
| Regulation of compute payments | Utility token for routing fee — not a security |
| AI agent adoption slower than expected | B2B dev tools route also (not just autonomous agents) |
| Existing players pivot to aggregation | 6–12 month lead time to replicate deep integrations |
