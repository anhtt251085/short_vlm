"""Consent and rights ledger.

Every voice recording must belong to a speaker who signed consent for the intended use,
and every training clip must come from an asset we have rights to. The data tools call
`check()` for every item and reject anything that fails.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCOPES = ("tts_training", "voice_conversion", "video_training", "image_training", "commercial_use")


@dataclass
class Record:
    id: str
    scopes: list[str]
    revoked: bool = False
    signed: dt.date | None = None
    expires: dt.date | None = None
    contract_ref: str | None = None
    accent: str | None = None
    voice_types: list[str] = field(default_factory=list)
    kind: str = "speaker"

    def check(self, needed: list[str], today: dt.date | None = None) -> tuple[bool, str]:
        today = today or dt.date.today()
        if self.revoked:
            return False, f"{self.kind} '{self.id}' revoked consent"
        if self.signed and self.signed > today:
            return False, f"{self.kind} '{self.id}' consent starts {self.signed}"
        if self.expires and self.expires < today:
            return False, f"{self.kind} '{self.id}' consent expired {self.expires}"
        missing = [s for s in needed if s not in self.scopes]
        if missing:
            return False, f"{self.kind} '{self.id}' consent does not cover: {', '.join(missing)}"
        return True, "ok"


def _date(value) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


class Ledger:
    def __init__(self, speakers: dict[str, Record], assets: dict[str, Record]):
        self.speakers = speakers
        self.assets = assets

    @classmethod
    def load(cls, path: str | Path) -> "Ledger":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

        def build(items, kind):
            out = {}
            for raw in items or []:
                scopes = list(raw.get("scopes") or [])
                bad = [s for s in scopes if s not in SCOPES]
                if bad:
                    raise ValueError(f"{kind} '{raw.get('id')}': unknown scopes {bad}")
                out[raw["id"]] = Record(
                    id=raw["id"], scopes=scopes, revoked=bool(raw.get("revoked", False)),
                    signed=_date(raw.get("signed")), expires=_date(raw.get("expires")),
                    contract_ref=raw.get("contract_ref"), accent=raw.get("accent"),
                    voice_types=list(raw.get("voice_types") or []), kind=kind,
                )
            return out

        return cls(build(data.get("speakers"), "speaker"), build(data.get("assets"), "asset"))

    def check_speaker(self, speaker_id: str, needed: list[str], today: dt.date | None = None):
        rec = self.speakers.get(speaker_id)
        if rec is None:
            return False, f"speaker '{speaker_id}' has no consent record"
        return rec.check(needed, today)

    def check_asset(self, asset_id: str, needed: list[str], today: dt.date | None = None):
        rec = self.assets.get(asset_id)
        if rec is None:
            return False, f"asset '{asset_id}' has no rights record"
        return rec.check(needed, today)


def needed_scopes(base: str, mode: str) -> list[str]:
    """Scopes required for an item, e.g. ['tts_training', 'commercial_use'] in commercial mode."""
    return [base, "commercial_use"] if mode == "commercial" else [base]
