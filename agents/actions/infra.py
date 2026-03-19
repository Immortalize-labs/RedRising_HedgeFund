"""
Infrastructure Actions
======================
Service restart and health actions for the AgentSupervisor.
"""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def restart_service(
    agent_id: str,
    check: str,
    strategy: str,
    detail: str,
    service_name: str = "",
    **kwargs,
) -> dict:
    """
    Restart a systemd service.

    Requires service_name kwarg (typically from action spec params).
    """
    if not service_name:
        logger.warning("[%s] restart_service called without service_name", agent_id)
        return {"success": False, "detail": "no service_name provided"}

    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"success": True, "detail": f"restarted {service_name}"}
        else:
            return {
                "success": False,
                "detail": f"restart failed rc={result.returncode}: {result.stderr}",
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "detail": f"restart timed out for {service_name}"}
    except FileNotFoundError:
        return {"success": False, "detail": "systemctl not found (not on Linux?)"}
    except Exception as e:
        return {"success": False, "detail": str(e)}
