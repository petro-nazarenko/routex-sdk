"""Shared domain types for RouteX SDK."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ComputeProvider(str, Enum):
    AKASH   = "akash"
    NOSANA  = "nosana"
    IONET   = "ionet"
    AETHIR  = "aethir"


class JobStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    TIMEOUT    = "timeout"


@dataclass
class JobRequest:
    """What the AI agent wants to run."""
    model: str                          # e.g. "meta-llama/Llama-3-70b"
    input_data: dict                    # prompt / task payload
    gpu_vram_gb: int = 24               # minimum VRAM required
    max_price_usd: float = 1.0          # hard ceiling per job
    max_latency_ms: int = 30_000        # SLA: give up if no response within N ms
    timeout_s: int = 300                # job execution timeout
    # Optional: pin to specific provider (skips routing, for testing)
    preferred_provider: Optional[ComputeProvider] = None


@dataclass
class ProviderQuote:
    """Price + availability response from a single compute provider."""
    provider: ComputeProvider
    price_usd: float                    # cost for this specific job
    estimated_latency_ms: int
    available: bool
    endpoint: str                       # API endpoint to submit to
    # Reliability score 0.0–1.0 (historical uptime from provider registry)
    reliability_score: float = 1.0
    raw_response: dict = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of the routing algorithm."""
    winner: ProviderQuote
    all_quotes: list[ProviderQuote]
    routing_fee_usd: float              # RouteX protocol fee (1% of job price)
    score_breakdown: dict               # for transparency/debugging


@dataclass
class JobResult:
    """Outcome of a dispatched compute job."""
    job_id: str
    provider: ComputeProvider
    status: JobStatus
    output: Optional[dict]
    price_paid_usd: float
    latency_ms: int
    # Set after on-chain settlement
    settlement_tx: Optional[str] = None
