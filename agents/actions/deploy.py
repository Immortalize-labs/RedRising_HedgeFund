"""
Deploy Actions
==============
Rollback and deploy actions for the AgentSupervisor.
Rollbacks are escalated rather than executed automatically.
"""
from __future__ import annotations

import logging

from agents.actions.notify import send_escalation

logger = logging.getLogger(__name__)


def trigger_rollback(
    agent_id: str,
    check: str,
    strategy: str,
    detail: str,
    **kwargs,
) -> dict:
    """
    Escalate a rollback request.  Does NOT auto-rollback — sends alert to humans.
    Only Holiday (infra director) executes rollbacks after manual approval.
    """
    msg = (
        f"ROLLBACK REQUESTED for {strategy}: {detail}\n"
        f"Check: {check} | Agent: {agent_id}\n"
        f"Action: Review deploy logs and run rollback if confirmed."
    )
    logger.warning("[%s] rollback escalated: %s", agent_id, detail)
    notify_result = send_escalation(
        agent_id=agent_id,
        check=check,
        strategy=strategy,
        detail=msg,
        **kwargs,
    )
    return {"action": "escalated_rollback", "notify": notify_result}
