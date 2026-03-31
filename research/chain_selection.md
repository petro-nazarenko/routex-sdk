# Chain Selection

> Phase 0.3 Output

---

## Decision: **Base (L2 on Ethereum)**

---

## Evaluation Matrix

### Candidates evaluated
Ethereum, Base, Arbitrum, Solana, BNB Chain

### Scoring (1–10 per criterion)

| Criterion | Weight | Ethereum | Base | Arbitrum | Solana | BNB Chain |
|-----------|--------|----------|------|----------|--------|-----------|
| Gas cost for target users | 30% | 2 | 9 | 8 | 9 | 7 |
| EVM compatibility | 20% | 10 | 10 | 10 | 2 | 10 |
| Active ecosystem grants | 25% | 5 | 8 | 9 | 7 | 6 |
| Bridge liquidity | 25% | 10 | 8 | 8 | 5 | 6 |
| **Weighted score** | | **6.35** | **8.80** | **8.75** | **6.10** | **7.25** |

### Gas cost detail (weight: 30%)
Our protocol does high-frequency micro-settlements: each compute job = 1 on-chain transaction.
At 100 agent jobs/day per agent, 250k active agents → millions of txs/day at scale.

| Chain | Avg tx cost | Cost per 1M txs |
|-------|-------------|-----------------|
| Ethereum | $2–20 | $2M–20M |
| Base | $0.001–0.01 | $1k–10k |
| Arbitrum | $0.01–0.05 | $10k–50k |
| Solana | $0.00025 | $250 |
| BNB Chain | $0.05–0.20 | $50k–200k |

Base wins on gas for EVM chains. Solana is cheaper but fails EVM compatibility.

### EVM compatibility detail (weight: 20%)
- **Base, Arbitrum, Ethereum, BNB:** Full EVM — existing Solidity tooling, OpenZeppelin, Hardhat/Foundry
- **Solana:** Rust/Anchor — complete rewrite of all EVM tooling, no OpenZeppelin, different audit surface

EVM required: our compute router integrates with ERC-8004 agent identity standard and ERC-20 payment tokens from Aethir/io.net ecosystems.

### Ecosystem grants detail (weight: 25%)
| Chain | Program | Amount | Relevance to our project |
|-------|---------|--------|--------------------------|
| Base | Builder Grants (retroactive 1–5 ETH) | Ongoing | ✅ DeFi primitives |
| Base | Builder Rewards | 2 ETH/week | ✅ Active builders |
| Base | Base Batches (founder program) | Significant | ✅ Early stage |
| Arbitrum | Trailblazer 2.0 | $1M ARB | ✅ Agentic DeFi — exact fit |
| Arbitrum | Stylus Sprint | 5M ARB | ⚠️ Requires WASM/Stylus |
| Arbitrum | Alchemy-Arbitrum | $10M credits | ⚠️ Orbit chains only |
| Solana | Superteam microgrants | $10k max | ⚠️ Small, EVM mismatch |

Base has structural grant advantage: Coinbase Corporate backing means grants are stable and not DAO-vote-dependent.
Arbitrum Trailblazer 2.0 is the most relevant single program but requires building on Vibekit (Ember framework) — vendor lock-in risk.

### Bridge liquidity detail (weight: 25%)
| Chain | Native bridge | 3rd party bridges | Daily bridge volume |
|-------|--------------|-------------------|---------------------|
| Base | Official Coinbase Bridge (unlimited) | Stargate, Across, Hop | High — Coinbase retail |
| Arbitrum | Official Arbitrum Bridge | Stargate, Across, Hop, Connext | Very high |
| Ethereum | N/A (native) | All | Highest |
| Solana | Wormhole, deBridge | Limited EVM compatibility | Medium |

Base and Arbitrum both score 8/10. Base has Coinbase Bridge advantage (zero slippage, institutional-grade, backed by $50B+ company). Arbitrum has more established DeFi bridge ecosystem.

---

## Why Base Wins

**1. Gas × Volume = economics**
Our protocol settles millions of compute jobs on-chain. At $0.001 avg gas, 1M txs = $1,000. Same on Arbitrum = $10,000–50,000. Economics favor Base by 10–50× at scale.

**2. Coinbase distribution = user acquisition path**
Coinbase Wallet has 10M+ active users. Base dapps appear natively in Coinbase interface. For AI agent developers (who often have Coinbase accounts), this is zero-cost distribution.

**3. Virtuals Protocol precedent**
Virtuals Protocol — the leading AI agent launchpad — deployed on Base and validated $479M in AI-driven economic activity. Our target users (AI agents) already live on Base.

**4. Superchain interoperability**
Base is part of the Optimism Superchain. As more rollups join (Zora, Mode, OP Mainnet), cross-chain agent routing becomes native via shared sequencing — directly useful for our multi-network compute routing mission.

**5. Growth trajectory**
DeFiLlama live data (March 2026): Base TVL = $3.97B, fastest growing L2 in 2025 (from $3.1B to $5.6B peak). Developer activity compounding.

---

## Why Not Arbitrum
- Trailblazer 2.0 grant is attractive but locks us into Ember/Vibekit framework
- TVL ($1.92B) declining relative to Base
- Slightly higher gas costs (3–5×)
- No Coinbase distribution advantage

## Why Not Solana
- Non-EVM: can't use ERC-8004, ERC-20 compute tokens, or OpenZeppelin
- Wormhole bridge has had security incidents ($325M hack 2022)
- Separate developer ecosystem from our target (AI agent devs largely EVM-native)

## Why Not Ethereum
- Gas makes micro-settlement economics impossible ($2–20/tx)
- Compute job aggregation at scale requires L2

---

## Final Answer

**Deploy on Base (Ethereum L2)**

- Token: ERC-20 on Base
- Bridge: Official Coinbase Bridge + Stargate for cross-chain liquidity
- Tooling: Foundry + OpenZeppelin + Hardhat (EVM standard)
- Grant target: Base Builder Grants (retroactive) + apply to Arbitrum Trailblazer if willing to port
