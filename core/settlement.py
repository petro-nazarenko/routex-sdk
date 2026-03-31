"""
Settlement hook — pluggable, token-agnostic.

Replace this stub with your on-chain settlement logic.
See routex-protocol/contracts/src/BurnVault.sol for the RouteX Protocol
reference implementation (ERC-20 fee burn + staker distribution on Base).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class OnChainSettlement:
    """
    Stub settlement handler.
    Implement settle() to trigger on-chain fee distribution after a job completes.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run

    async def settle(self, job_price_usd: float, job_id: str) -> str | None:
        # TODO: settlement hook — pluggable, token-agnostic
        # Reference implementation: routex-protocol/contracts/src/BurnVault.sol
        if self._dry_run:
            logger.info("[DRY_RUN] Would settle job=%s price=$%.4f", job_id, job_price_usd)
        return None
