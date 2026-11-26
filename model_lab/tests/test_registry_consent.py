import datetime as dt

import pytest

from modellab.consent import Ledger, needed_scopes
from modellab.registry import LicenceError, Registry


def test_registry_parses_yes_no_and_gates_commercial(models_path):
    reg = Registry.load(models_path)
    assert reg.get("wan2.1-t2v-1.3b").commercial_ok == "yes"
    assert reg.get("f5-tts-vietnamese").commercial_ok == "no"
    assert reg.get("vieneu-tts-v3-turbo").commercial_ok == "check"
    assert reg.require("melotts-vietnamese", "commercial").id == "melotts-vietnamese"
    with pytest.raises(LicenceError, match="does not allow commercial use"):
        reg.require("f5-tts-vietnamese", "commercial")
    with pytest.raises(LicenceError, match="unverified"):
        reg.require("vieneu-tts-v3-turbo", "commercial")


def test_research_mode_allows_with_warning(models_path):
    reg = Registry.load(models_path)
    ok, reason = reg.get("f5-tts-vietnamese").allowed("research")
    assert ok and "research only" in reason


def test_unknown_model(models_path):
    with pytest.raises(KeyError):
        Registry.load(models_path).get("nope")


def test_consent_rules(ledger_path):
    led = Ledger.load(ledger_path)
    commercial = needed_scopes("tts_training", "commercial")
    assert led.check_speaker("spk_north_m01", commercial)[0]
    ok, why = led.check_speaker("spk_research_only", commercial)
    assert not ok and "commercial_use" in why
    assert led.check_speaker("spk_research_only", needed_scopes("tts_training", "research"))[0]
    ok, why = led.check_speaker("spk_revoked", commercial)
    assert not ok and "revoked" in why
    ok, why = led.check_speaker("stranger", commercial)
    assert not ok and "no consent record" in why


def test_consent_dates(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("speakers:\n  - id: a\n    signed: 2030-01-01\n    scopes: [tts_training]\n"
                 "  - id: b\n    signed: 2020-01-01\n    expires: 2021-01-01\n    scopes: [tts_training]\n")
    led = Ledger.load(p)
    today = dt.date(2026, 11, 26)
    assert "starts" in led.check_speaker("a", ["tts_training"], today)[1]
    assert "expired" in led.check_speaker("b", ["tts_training"], today)[1]


def test_unknown_scope_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("speakers:\n  - id: a\n    scopes: [everything]\n")
    with pytest.raises(ValueError, match="unknown scopes"):
        Ledger.load(p)
