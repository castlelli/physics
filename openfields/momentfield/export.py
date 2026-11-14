"""JSON contract shared with the future front-end, plus the golden parity fixture.

Samples carry ``plane``, ``ray`` and ``radius`` indices so the front-end can
filter sections and highlight rays without recomputing — do not strip them.
"""

from __future__ import annotations

import json
from pathlib import Path

from momentfield.sampling import SampledField, SamplingConfig, sample_field

# reference configuration for the golden fixture — changing it breaks TS parity,
# regenerate the fixture and rerun the parity test if it ever has to move
GOLDEN_FORCE_POINT = (1.0, -0.5, 2.0)
GOLDEN_FORCE = (2.0, 1.0, -1.5)
GOLDEN_CONFIG = SamplingConfig(
    n_planes=3,
    plane_spacing=1.5,
    angle_step_deg=60.0,
    n_radii=2,
    radius_step=1.0,
)


def field_to_contract(field: SampledField) -> dict:
    """Serialize a sampled field to the JSON contract (plain lists, full precision)."""
    cfg = field.config
    return {
        "force_point": field.force_point.tolist(),
        "force": field.force.tolist(),
        "basis": {
            "u": field.basis.u.tolist(),
            "v1": field.basis.v1.tolist(),
            "v2": field.basis.v2.tolist(),
        },
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


def write_field_json(field: SampledField, path: str | Path) -> None:
    Path(path).write_text(json.dumps(field_to_contract(field), indent=2), encoding="utf-8")


def write_golden_fixture(path: str | Path) -> SampledField:
    """Export the reference configuration used by the TS parity test."""
    field = sample_field(GOLDEN_CONFIG, GOLDEN_FORCE_POINT, GOLDEN_FORCE)
    write_field_json(field, path)
    return field
