"""Data for the live site (docs/wrench/data/golden.json): every case's inputs and outputs at full precision.

The site's model.js recomputes these; tests/test_paridade.py compares the two to 1e-12.
"""

from __future__ import annotations

import json
from pathlib import Path

from .casos import BOX, CASES
from .modelo import Reduction, System, reduce

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT.parent / "docs" / "wrench"


def optional(v):
    return None if v is None else v.tolist()


def case_contract(system: System, reduction: Reduction) -> dict:
    r = reduction
    return {
        "input": {
            "forces": system.forces.tolist(),
            "points": system.points.tolist(),
            "Q": system.pole_q.tolist(),
            "A": system.pole_a.tolist(),
            "u": system.u.tolist(),
            "box": [system.box.a, system.box.b, system.box.c],
        },
        "output": {
            "R": r.resultant.tolist(),
            "M_Q": r.moment_q.tolist(),
            "M_A": r.moment_a.tolist(),
            "unit_u": r.unit_u.tolist(),
            "axis_torque": r.axis_torque,
            "I": r.invariant,
            "category": r.category,
            "shape": list(r.shape),
            "axis_point": optional(r.axis_point),
            "axis_direction": optional(r.axis_direction),
            "M_E": optional(r.minimum_moment),
        },
    }


def golden() -> dict:
    cases = {}
    for key, case in CASES.items():
        system = case.system()
        cases[key] = {"expected": case.expected, "view": list(case.view), **case_contract(system, reduce(system))}
    return {"box": [BOX.a, BOX.b, BOX.c], "cases": cases}


def export_site(target: Path = SITE_DIR) -> Path:
    data = target / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "golden.json").write_text(json.dumps(golden(), indent=1), encoding="utf-8")
    return target
