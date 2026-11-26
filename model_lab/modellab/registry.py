"""Model registry and licence gate.

In commercial mode only models whose licence is confirmed for commercial use may be
trained or shipped. In research mode everything is allowed, with a warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

MODES = ("commercial", "research")


class LicenceError(RuntimeError):
    pass


def _status(value: Any) -> str:
    # YAML 1.1 reads bare yes/no as booleans; accept both spellings.
    if value is True:
        return "yes"
    if value is False:
        return "no"
    value = str(value).strip().lower()
    if value not in ("yes", "no", "check"):
        raise ValueError(f"commercial_ok must be yes, no, or check, got {value!r}")
    return value


@dataclass
class ModelEntry:
    id: str
    task: str
    license: str
    commercial_ok: str
    source: str = ""
    trainer: str | None = None
    trainer_task: str | None = None
    needs_high_noise_dit: bool = False
    min_vram_gb: int | None = None
    languages: list[str] = field(default_factory=list)
    notes: str = ""

    def allowed(self, mode: str) -> tuple[bool, str]:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if mode == "research":
            if self.commercial_ok != "yes":
                return True, f"research only: licence is '{self.license}' ({self.commercial_ok})"
            return True, "ok"
        if self.commercial_ok == "yes":
            return True, "ok"
        if self.commercial_ok == "no":
            return False, f"licence '{self.license}' does not allow commercial use"
        return False, f"licence '{self.license}' is unverified; confirm it and set commercial_ok: yes"


class Registry:
    def __init__(self, entries: list[ModelEntry]):
        self.entries = {e.id: e for e in entries}

    @classmethod
    def load(cls, path: str | Path) -> "Registry":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        entries = []
        for raw in data.get("models", []):
            raw = dict(raw)
            raw["commercial_ok"] = _status(raw.get("commercial_ok", "check"))
            known = {k: v for k, v in raw.items() if k in ModelEntry.__dataclass_fields__}
            entries.append(ModelEntry(**known))
        return cls(entries)

    def get(self, model_id: str) -> ModelEntry:
        if model_id not in self.entries:
            raise KeyError(f"unknown model '{model_id}'. Known: {', '.join(sorted(self.entries))}")
        return self.entries[model_id]

    def by_task(self, task: str | None = None) -> list[ModelEntry]:
        return [e for e in self.entries.values() if task is None or e.task == task]

    def require(self, model_id: str, mode: str) -> ModelEntry:
        """Return the model if allowed in this mode, otherwise raise LicenceError."""
        entry = self.get(model_id)
        ok, reason = entry.allowed(mode)
        if not ok:
            raise LicenceError(f"{model_id}: {reason}")
        return entry
