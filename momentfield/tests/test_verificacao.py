"""The proof harness passes for varied inputs; the report's claims hold; the JSON contract round-trips."""

import json

import numpy as np
import pytest

from codigo import relatorio
from codigo.casos import CASES, GOLDEN_CONFIG, GOLDEN_FORCE, GOLDEN_FORCE_POINT
from codigo.modelo import SamplingConfig, sample_field
from codigo.site import export_site, field_to_contract
from codigo.verificacao import run_proofs


@pytest.mark.parametrize(
    ("point", "force"),
    [((0.0, 0.0, 0.0), (0.0, 0.0, 5.0)), ((1.0, -0.5, 2.0), (2.0, 1.0, -1.5)), ((-3.0, 4.0, 1.0), (1e3, -2e3, 0.5e3))],
)
def test_axisymmetry_proofs_pass(point, force):
    report = run_proofs(np.array(point), np.array(force))
    assert report.passed, report.relative()


@pytest.mark.parametrize("key", sorted(CASES))
def test_report_claims_hold_for_every_case(key):
    case = CASES[key]
    field = sample_field(case.config, case.force_point, case.force)
    assert relatorio.plane_spread(field) < 1e-12
    assert relatorio.rotation_spread(field) < 1e-12
    assert relatorio.axial_line_error(field) < 1e-12


def test_rotation_check_catches_a_step_that_is_not_a_symmetry():
    # with a 45° step, rotating by 45° maps the plane onto itself; rotating a 60° layout by 45° would not
    field = sample_field(SamplingConfig(angle_step_deg=45.0), (0, 0, 0), (0, 0, 1))
    assert relatorio.rotation_spread(field) < 1e-12
    shifted = sample_field(SamplingConfig(angle_step_deg=60.0), (0, 0, 0), (0, 0, 1))
    object.__setattr__(shifted, "config", SamplingConfig(angle_step_deg=45.0))
    assert relatorio.rotation_spread(shifted) > 0.1


def test_site_export_writes_the_golden_fixture_at_full_precision(tmp_path):
    export_site(tmp_path)
    loaded = json.loads((tmp_path / "data" / "golden.json").read_text(encoding="utf-8"))
    field = sample_field(GOLDEN_CONFIG, GOLDEN_FORCE_POINT, GOLDEN_FORCE)
    assert loaded == field_to_contract(field)  # JSON floats round-trip exactly
    for key in ("plane", "ray", "radius"):
        assert key in loaded["samples"]
    report = json.loads((tmp_path / "data" / "report.json").read_text(encoding="utf-8"))
    assert set(report["cases"]) == set(CASES)
    assert all(max(c["proof"]["relative"].values()) < 1e-12 for c in report["cases"].values())
