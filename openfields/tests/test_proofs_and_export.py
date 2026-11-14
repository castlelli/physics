"""Proof harness passes for varied inputs; JSON contract round-trips exactly."""

import json

import numpy as np
import pytest

from momentfield.export import (
    GOLDEN_CONFIG,
    GOLDEN_FORCE,
    GOLDEN_FORCE_POINT,
    field_to_contract,
    write_golden_fixture,
)
from momentfield.proofs import run_proofs
from momentfield.sampling import sample_field


@pytest.mark.parametrize(
    ("point", "force"),
    [
        ((0.0, 0.0, 0.0), (0.0, 0.0, 5.0)),
        ((1.0, -0.5, 2.0), (2.0, 1.0, -1.5)),
        ((-3.0, 4.0, 1.0), (1e3, -2e3, 0.5e3)),
    ],
)
def test_axisymmetry_proofs_pass(point, force):
    report = run_proofs(np.array(point), np.array(force),
                        tolerance=1e-9 * max(1.0, np.linalg.norm(force)))
    assert report.passed, report


def test_golden_fixture_round_trips_at_full_precision(tmp_path):
    path = tmp_path / "golden.json"
    field = write_golden_fixture(path)
    loaded = json.loads(path.read_text(encoding="utf-8"))

    recomputed = sample_field(GOLDEN_CONFIG, GOLDEN_FORCE_POINT, GOLDEN_FORCE)
    contract = field_to_contract(recomputed)

    assert loaded == contract  # JSON floats round-trip exactly (repr precision)
    assert np.abs(np.array(loaded["samples"]["moments"]) - field.moments).max() == 0.0
    assert loaded["samples"]["plane"] == field.plane_index.tolist()
    assert loaded["samples"]["ray"] == field.ray_index.tolist()
    assert loaded["samples"]["radius"] == field.radius_index.tolist()
