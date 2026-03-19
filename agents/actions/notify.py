"""
Notification Actions
====================
Discord and Telegram escalation actions for the AgentSupervisor.

Used in manifests as::

    module: agents.actions.notify
    function: send_escalation
"""
from __future__ import annotations

import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)


def _get_discord_sender() -> Callable | None:
    """Return Discord send function if webhook is configured."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return None

    def send(msg: str) -> bool:
        try:
            import requests
            resp = requests.post(url, json={"content": msg}, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning("Discord send failed: %s", e)
            return False

    return send


def _get_telegram_sender() -> Callable | None:
    """Return Telegram send function if bot token is configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return None

    def send(msg: str) -> bool:
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)
            return False

    return send


def send_escalation(
    agent_id: str,
    check: str,
    strategy: str,
    detail: str,
    **kwargs,
) -> dict:
    """
    Send an escalation alert to Discord and/or Telegram.

    Returns:
        dict with keys: success (bool), sent_to (list[str])
    """
    msg = f"[{agent_id.upper()}] ESCALATION — {check} | {strategy}\n{detail}"
    sent_to = []

    discord = _get_discord_sender()
    if discord and discord(msg):
        sent_to.append("discord")

    telegram = _get_telegram_sender()
    if telegram and telegram(msg):
        sent_to.append("telegram")

    success = len(sent_to) > 0
    if not success:
        logger.warning("[%s] escalation not sent — no channels configured", agent_id)

    return {"success": success, "sent_to": sent_to, "detail": detail}
