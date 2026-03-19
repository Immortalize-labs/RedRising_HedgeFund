"""
Strategy Registry — Typed Python loader for config/strategies.yaml
===================================================================
Single import, zero hardcoded paths. Every consumer uses this.

Usage:
    from config.strategy_registry import registry

    registry.get("ETHXGB05M01")           # one strategy
    registry.active()                      # active only
    registry.alive()                       # active + stopped
    registry.settlement_paths()            # drop-in for telegram_reporter
    registry.settlement_paths_with_trades()  # drop-in for risk_reporter
    registry.services()                    # drop-in for health_monitor SERVICES
    registry.log_files()                   # drop-in for health_monitor LOG_FILES
    registry.qa_audit_configs()            # drop-in for qa_strategy_audit
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "strategies.yaml"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WalletConfig:
    id: str
    env_var: str
    fallback: str

    def address(self) -> str:
        return os.environ.get(self.env_var, self.fallback)


@dataclass(frozen=True)
class SettlementConfig:
    slug_filter: str  # "include", "exclude", "all"
    slug_match: str = ""
    slug_exclude: tuple[str, ...] = ()
    poll_interval_s: int = 60
    kelly_band_analysis: bool = False
    kelly_trades_file: str = ""


@dataclass(frozen=True)
class Strategy:
    id: str
    display_name: str
    asset: str
    model: str
    timeframe: str
    version: int
    status: str  # "active", "stopped", "killed"
    wallet_id: str
    slug_prefix: str
    window_seconds: int
    trade_dir: str
    settlement_file: str
    trades_file: str
    log_file: str
    settlement: SettlementConfig
    systemd_trader: str
    systemd_settlement: str
    trader_script: str
    model_path: str = ""
    features_path: str = ""
    primary_symbol: str = ""
    cross_symbol: str = ""
    resample: str = ""
    strategy_start: str = ""

    # Populated after construction
    _wallet: Optional[WalletConfig] = field(default=None, repr=False, compare=False)

    @property
    def wallet(self) -> WalletConfig:
        assert self._wallet is not None
        return self._wallet

    @property
    def wallet_address(self) -> str:
        return self.wallet.address()

    @property
    def settlement_path(self) -> Path:
        return _PROJECT_ROOT / self.settlement_file

    @property
    def trade_dir_path(self) -> Path:
        return _PROJECT_ROOT / self.trade_dir

    @property
    def trades_path(self) -> Path:
        return _PROJECT_ROOT / self.trades_file

    @property
    def log_path(self) -> Path:
        return _PROJECT_ROOT / self.log_file

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_alive(self) -> bool:
        """Active or stopped — still needs settlement checking."""
        return self.status in ("active", "stopped")

    @property
    def is_killed(self) -> bool:
        return self.status == "killed"


# ── Registry ─────────────────────────────────────────────────────────────────

class StrategyRegistry:
    """Singleton registry loaded from strategies.yaml."""

    def __init__(self, yaml_path: Path | None = None):
        self._yaml_path = yaml_path or _YAML_PATH
        self._strategies: dict[str, Strategy] = {}
        self._wallets: dict[str, WalletConfig] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    def _load(self):
        with open(self._yaml_path) as f:
            raw = yaml.safe_load(f)

        # Parse wallets
        for wid, wdata in raw.get("wallets", {}).items():
            self._wallets[wid] = WalletConfig(
                id=wid,
                env_var=wdata["env_var"],
                fallback=wdata["fallback"],
            )

        # Parse strategies
        for sid, sdata in raw.get("strategies", {}).items():
            # Parse settlement config
            sconf_raw = sdata.get("settlement", {})
            sconf = SettlementConfig(
                slug_filter=sconf_raw.get("slug_filter", "all"),
                slug_match=sconf_raw.get("slug_match", ""),
                slug_exclude=tuple(sconf_raw.get("slug_exclude", [])),
                poll_interval_s=sconf_raw.get("poll_interval_s", 60),
                kelly_band_analysis=sconf_raw.get("kelly_band_analysis", False),
                kelly_trades_file=sconf_raw.get("kelly_trades_file", ""),
            )

            wallet_ref = sdata.get("wallet", "")
            wallet_obj = self._wallets.get(wallet_ref)

            strategy = Strategy(
                id=sid,
                display_name=sdata["display_name"],
                asset=sdata["asset"],
                model=sdata["model"],
                timeframe=sdata["timeframe"],
                version=sdata["version"],
                status=sdata["status"],
                wallet_id=wallet_ref,
                slug_prefix=sdata.get("slug_prefix", ""),
                window_seconds=sdata.get("window_seconds", 300),
                trade_dir=sdata["trade_dir"],
                settlement_file=sdata["settlement_file"],
                trades_file=sdata["trades_file"],
                log_file=sdata["log_file"],
                settlement=sconf,
                systemd_trader=sdata.get("systemd_trader", ""),
                systemd_settlement=sdata.get("systemd_settlement", ""),
                trader_script=sdata.get("trader_script", ""),
                model_path=sdata.get("model_path", ""),
                features_path=sdata.get("features_path", ""),
                primary_symbol=sdata.get("primary_symbol", ""),
                cross_symbol=sdata.get("cross_symbol", ""),
                resample=sdata.get("resample", ""),
                strategy_start=sdata.get("strategy_start", ""),
                _wallet=wallet_obj,
            )
            self._strategies[sid] = strategy

        self._loaded = True

    # ── Lookups ──────────────────────────────────────────────────────────────

    def get(self, strategy_id: str) -> Strategy:
        self._ensure_loaded()
        return self._strategies[strategy_id]

    def all(self) -> list[Strategy]:
        self._ensure_loaded()
        return list(self._strategies.values())

    def active(self) -> list[Strategy]:
        self._ensure_loaded()
        return [s for s in self._strategies.values() if s.is_active]

    def alive(self) -> list[Strategy]:
        self._ensure_loaded()
        return [s for s in self._strategies.values() if s.is_alive]

    def killed(self) -> list[Strategy]:
        self._ensure_loaded()
        return [s for s in self._strategies.values() if s.is_killed]

    def by_wallet(self, wallet_id: str) -> list[Strategy]:
        self._ensure_loaded()
        return [s for s in self._strategies.values() if s.wallet_id == wallet_id]

    def by_display_name(self, name: str) -> Strategy | None:
        self._ensure_loaded()
        for s in self._strategies.values():
            if s.display_name == name:
                return s
        return None

    def wallet(self, wallet_id: str) -> WalletConfig:
        self._ensure_loaded()
        return self._wallets[wallet_id]

    # ── Drop-in replacement dicts ────────────────────────────────────────────

    def settlement_paths(self, include_killed: bool = False) -> dict[str, str]:
        """
        Drop-in for telegram_reporter / discord_morning_brief / drawdown_monitor.
        Returns {display_name: relative_settlement_path}.
        """
        self._ensure_loaded()
        return {
            s.display_name: s.settlement_file
            for s in self._strategies.values()
            if include_killed or not s.is_killed
        }

    def settlement_paths_with_trades(
        self, include_killed: bool = False,
    ) -> dict[str, dict[str, str]]:
        """
        Drop-in for risk_reporter.
        Returns {display_name: {"settlement": ..., "trades": ..., "wallet": ...}}.
        """
        self._ensure_loaded()
        return {
            s.display_name: {
                "settlement": s.settlement_file,
                "trades": s.trades_file,
                "wallet": s.wallet_id,
            }
            for s in self._strategies.values()
            if include_killed or not s.is_killed
        }

    def services(self) -> list[str]:
        """
        Drop-in for health_monitor SERVICES list.
        Returns systemd trader service names for active strategies.
        """
        self._ensure_loaded()
        return [s.systemd_trader for s in self._strategies.values() if s.is_active]

    def log_files(self) -> dict[str, str]:
        """
        Drop-in for health_monitor LOG_FILES dict.
        Returns {display_name: relative_log_path} for active strategies.
        """
        self._ensure_loaded()
        return {
            s.display_name: s.log_file
            for s in self._strategies.values()
            if s.is_active
        }

    def qa_audit_configs(self) -> dict[str, dict]:
        """
        Drop-in for qa_strategy_audit STRATEGIES dict.
        Returns configs for XGB strategies only (have model/features).
        """
        self._ensure_loaded()
        result = {}
        for s in self._strategies.values():
            if not s.is_active or not s.model_path:
                continue
            cfg = {
                "model": Path(s.model_path).name,
                "features": Path(s.features_path).name,
                "primary_symbol": s.primary_symbol,
                "cross_symbol": s.cross_symbol,
                "interval": "5m",  # all strategies fetch 5m klines
                "trader_script": Path(s.trader_script).name,
            }
            if s.resample:
                cfg["resample"] = s.resample
            result[s.display_name] = cfg
        return result


# ── Module-level singleton ───────────────────────────────────────────────────

registry = StrategyRegistry()
