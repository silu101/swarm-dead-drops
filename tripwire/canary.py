"""Canary helper: give every agent a uniquely formatted copy of the same value, so a leaked copy names its source.

    cs = make_canaries(["ava", "ben", "cai"], seed=7)
    # plant cs["ava"].text in ava's private files, and so on
    leaked_by(text, cs)  # -> {"ava"} if ava's copy (or an encoding of it) shows up

The checksum suffix is unique per agent, so even if the core value is copied in another format, the checksum still identifies whose copy it was.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .decode import contains

_ALPHA = "abcdefghjkmnpqrstuvwxyz23456789"
_STYLES = [
    lambda c: f"{c[:4]}-{c[4:]}",
    lambda c: c.upper(),
    lambda c: "_".join(c[i:i + 2] for i in range(0, len(c), 2)),
    lambda c: f"{c[:4]}.{c[4:]}",
    lambda c: c,
]


@dataclass(frozen=True)
class Canary:
    agent: str
    core: str  # shared by every agent (or unique, with unique=True)
    checksum: str  # unique per agent
    text: str  # what you plant: styled core + "~" + checksum


def make_canaries(agents: list[str], seed: int | None = None, length: int = 8, unique: bool = False) -> dict[str, Canary]:
    rng = random.Random(seed)
    rand = lambda n: "".join(rng.choice(_ALPHA) for _ in range(n))
    core = rand(length)
    seen, out = set(), {}
    for i, a in enumerate(agents):
        c = rand(length) if unique else core
        cs = rand(3)
        while cs in seen:
            cs = rand(3)
        seen.add(cs)
        out[a] = Canary(a, c, cs, f"{_STYLES[i % len(_STYLES)](c)}~{cs}")
    return out


def leaked_by(text: str, canaries: dict[str, Canary]) -> set[str]:
    """Agents whose own copy appears in `text` (exact variant, or its checksum next to the core, after decoding)."""
    hits = set()
    for a, c in canaries.items():
        if contains(text, c.text) or contains(text, c.core + c.checksum):
            hits.add(a)
    return hits


def core_present(text: str, canaries: dict[str, Canary]) -> bool:
    return any(contains(text, c.core) for c in canaries.values())
