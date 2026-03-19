from unittest.mock import MagicMock, patch
import time
from core.monitor.cycle import CycleMonitor

class DummySignal:
    prediction = "UP"
    probability = 0.55
    confidence = 0.55
    asset_price = 1.0

class DummySize:
    shares = 100
    notional = 100.0

class DummyVerdict:
    reason = "Mocked verdict"
    allowed = True

def test_run_cycle_skip_trade():
    prediction = MagicMock()
    prediction.predict.return_value = DummySignal()

    sizing = MagicMock()
    sizing.compute.return_value = DummySize()
    sizing.min_prob = 0.6  # Provide the attribute!

    risk_gate = MagicMock()
    risk_gate.check_kill_file.return_value = None
    risk_gate.pm_veto_mode = "shadow"
    risk_gate.check_pm_veto.return_value = DummyVerdict()

    executor = MagicMock()
    executor.has_pending = False
    executor.execute.return_value = None  # Force None to trigger logging

    monitor = CycleMonitor(
        prediction=prediction,
        sizing=sizing,
        risk_gate=risk_gate,
        executor=executor,
        slug_prefix="btc",
        window_seconds=300,
        min_remaining_s=90,
        asset="BTC",
        interval="5m",
        price_field="btc_price",
        min_confidence_prob=0.52,
    )
    
    # We must ensure the cycle check actually runs
    # current_epoch > last_traded_epoch
    monitor.last_traded_epoch = 0

    with patch('core.monitor.cycle.time.time') as mock_time, \
         patch('core.monitor.cycle.find_market') as mock_find_market:
        
        mock_time.return_value = 300  # Epoch 300 > 0
        mock_find_market.return_value = {"remaining_sec": 100, "yes_price": 0.5}

        # Run cycle
        monitor.run_cycle()

        # Ascertain that log_skip was called, which validates that `self.sizing` didn't error!
        executor.log_skip.assert_called_once()
