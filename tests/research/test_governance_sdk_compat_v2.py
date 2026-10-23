from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from experiments import run_a_share_price_volume_retro_real_v1 as runner
from experiments.a_share_ingestion import retro_capture_v1 as capture

ROOT = Path(__file__).resolve().parents[2]


def test_sdk_binding_v2_is_explicit_and_preserves_v1() -> None:
    assert runner.CATALOG_GOVERNANCE_SDK_BINDING == "platform-audit-remediation-20261022-v2"
    assert runner.CATALOG_GOVERNANCE_CODE_PINS == {
        "foundation/src/crypto_quant_foundation/storage.py": "a33939d07f34d9a2b2beec491512a822c025a5279a8750ff3fc89540f45774e7",
        "research-platform/src/crypto_quant_research/retrospective_study.py": "31497d3917bd5da6b395a1db4e2c8f550d392b195fc9c041cdb400980092738e",
        "research-platform/src/crypto_quant_research/statistical_study.py": "9b8f726936f17ea8e46815ae0afd25006b7df8fa0bf81f2df30b6e5ebade26b0",
        "strategy-validation/src/crypto_quant_validation/retrospective_reservation.py": "89f6b99b49255b4c5f4580174b11df7bc86eae24ac0d0b23813f39760ab72067",
        "strategy-validation/src/crypto_quant_validation/statistical_reservation.py": "f73c4cbeb1d3e55ea8c178066d0cfa5c4d680db1b3dcdc293e6bf1c4d09df8dd",
        "strategy-validation/src/crypto_quant_validation/sample_consumption.py": "082f9f4629cf15d707d97cbd1a85c440708d3ad80b1edba899e72db1a4ce3234",
        "strategy-validation/src/crypto_quant_validation/ledger.py": "4e3a6d3ab2c8c22e986df40c56b49fe2cd48693038f824cf2319b17b3f46c0e9",
    }
    assert len(runner.CATALOG_GOVERNANCE_CODE_PINS_V1) == 7
    assert runner.CATALOG_GOVERNANCE_SDK_REVISIONS == {
        "foundation": "9d88ed67a84d06c558276f8bae2206b069bcec8f",
        "research-platform": "ba2af01b7e070a677b7f365ef37f7d8a6a071ff6",
        "strategy-validation": "fa16b688cc1468007c2f92e2c53079bc4ab5464d",
    }
    for relative, expected in runner.CATALOG_GOVERNANCE_CODE_PINS.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert runner.CATALOG_GOVERNANCE_CODE_PINS_V1 == {
        **runner.CATALOG_GOVERNANCE_CODE_PINS,
        "strategy-validation/src/crypto_quant_validation/retrospective_reservation.py": "bd9ba06528f53e0071bffe5190536214f403f44a80920f2173795ce84b6d72fb",
        "strategy-validation/src/crypto_quant_validation/statistical_reservation.py": "5bd9f097bb7eb329bc458972876f901a90b34a383a667a589bdd2ce21ceceb23",
        "strategy-validation/src/crypto_quant_validation/ledger.py": "94c4beabba6d6583837b7b5a607fa63a84266c33b01b3964ecbc8e18f0e2a4f3",
    }


def test_historic_v1_pins_cannot_authorize_current_capture(tmp_path, monkeypatch) -> None:
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=False)
    protocol = capture.synthetic_capture_protocol(spec)
    monkeypatch.setattr(runner, "CATALOG_GOVERNANCE_CODE_PINS", dict(runner.CATALOG_GOVERNANCE_CODE_PINS_V1))
    with pytest.raises(capture.CaptureError, match="CAPTURE_GOV_CODE_PIN"):
        capture.issue_capture_admission(spec, protocol, runtime_authorize=lambda: None)
    assert (Path(spec.output) / "governance-account/close.json").exists()
    assert not (Path(spec.output) / "data").exists()


def test_ledger_foundation_guard_is_pure_identity_check(tmp_path, monkeypatch) -> None:
    from crypto_quant_foundation import LocalFoundation
    from crypto_quant_validation import SampleConsumptionLedger, ValidationCoreFailure

    def no_clock():
        raise AssertionError("guard must not read clock")

    first = LocalFoundation(tmp_path / "first", clock=no_clock)
    second = LocalFoundation(tmp_path / "second", clock=no_clock)
    ledger = SampleConsumptionLedger(first)
    monkeypatch.setattr(Path, "stat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("filesystem I/O")))
    monkeypatch.setattr(Path, "open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("filesystem I/O")))
    ledger.require_foundation(first)
    with pytest.raises(ValidationCoreFailure) as failure:
        ledger.require_foundation(second)
    assert failure.value.code == "SAMPLE_LEDGER_CONFLICT"
