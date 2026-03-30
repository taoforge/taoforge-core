"""Structured logging setup for TaoForge neurons."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO", debug: bool = False) -> None:
    """Initialize structured logging for TaoForge.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        debug: Enable debug-level logging (overrides level).
    """
    if debug:
        level = "DEBUG"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logging.getLogger(__name__).info("TaoForge logging initialized.")


def log_proposal_event(
    event: str,
    proposal_id: str,
    agent_id: str = "",
    **kwargs: object,
) -> None:
    """Log a proposal lifecycle event with structured fields."""
    logger = logging.getLogger("taoforge.proposal")
    fields = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(
        f"[PROPOSAL] {event} | id={proposal_id} | agent={agent_id[:16]}... | {fields}"
    )


def log_eval_event(
    event: str,
    suite_id: str = "",
    **kwargs: object,
) -> None:
    """Log an evaluation event with structured fields."""
    logger = logging.getLogger("taoforge.evaluation")
    fields = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"[EVAL] {event} | suite={suite_id} | {fields}")
