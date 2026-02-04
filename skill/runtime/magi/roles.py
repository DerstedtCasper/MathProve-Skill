"""Role definitions for Math MAGI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MagiRole:
    key: str
    title: str
    focus: list[str]
    veto_triggers: list[str]


DEFAULT_ROLES = [
    MagiRole(
        key="melchior",
        title="MELCHIOR-FORMAL",
        focus=["formalization", "mathlib", "lemma selection"],
        veto_triggers=["undefined symbols", "missing lemma plan"],
    ),
    MagiRole(
        key="balthasar",
        title="BALTHASAR-COMPUTE",
        focus=["sympy", "counterexample search", "algebra check"],
        veto_triggers=["missing compute check", "unsafe algebra step"],
    ),
    MagiRole(
        key="casper",
        title="CASPER-SKEPTIC",
        focus=["logic gaps", "hidden assumptions", "traceability"],
        veto_triggers=["missing evidence", "unclear dependency"],
    ),
]
