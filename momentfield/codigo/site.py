"""Data for the live site (docs/momentfield/data): the JSON contract, the parity fixture and the report numbers.

Samples carry ``plane``, ``ray`` and ``radius`` indices so the site can filter sections and highlight
rays without recomputing; do not strip them.
"""

from __future__ import annotations

import json
from pathlib import Path

from .casos import CASES, GOLDEN_CONFIG, GOLDEN_FORCE, GOLDEN_FORCE_POINT
from .modelo import SampledField, sample_field
from .verificacao import run_proofs

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT.parent / "docs" / "momentfield"


def field_to_contract(field: SampledField) -> dict:
    """Sampled field as plain lists at full precision (the JSON contract)."""
    cfg = field.config
    return {
        "force_point": field.force_point.tolist(),
        "force": field.force.tolist(),
        "basis": {"u": field.basis.u.tolist(), "v1": field.basis.v1.tolist(), "v2": field.basis.v2.tolist()},
        "config": {
            "n_planes": cfg.n_planes,
            "plane_spacing": cfg.plane_spacing,
            "angle_step_deg": cfg.angle_step_deg,
            "n_radii": cfg.n_radii,
            "radius_step": cfg.radius_step,
        },
        "samples": {
            "poles": field.poles.tolist(),
            "moments": field.moments.tolist(),
            "feet": field.feet.tolist(),
            "axial_offset": field.axial_offset.tolist(),
            "radial_distance": field.radial_distance.tolist(),
            "plane": field.plane_index.tolist(),
            "ray": field.ray_index.tolist(),
            "radius": field.radius_index.tolist(),
        },
    }


def golden_field() -> SampledField:
    return sample_field(GOLDEN_CONFIG, GOLDEN_FORCE_POINT, GOLDEN_FORCE)


def report_data() -> dict:
    """Ready-made cases and Python's proof residuals, which the site shows next to its own."""
    cases = {}
    for key, case in CASES.items():
        report = run_proofs(case.force_point, case.force)
        cases[key] = {
            "title": case.title,
            "force_point": list(case.force_point),
            "force": list(case.force),
            "config": field_to_contract(sample_field(case.config, case.force_point, case.force))["config"],
            "proof": {"n_poles": report.n_poles, "relative": report.relative()},
        }
    return {"cases": cases}


def export_site(target: Path = SITE_DIR) -> Path:
    data = target / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "golden.json").write_text(json.dumps(field_to_contract(golden_field())), encoding="utf-8")
    (data / "report.json").write_text(json.dumps(report_data(), indent=1, ensure_ascii=False), encoding="utf-8")
    return target
