"""Assertions on the pole sampling layout (planes × rays × radii)."""

import numpy as np
import pytest

from momentfield.core import line_basis
from momentfield.sampling import SamplingConfig, generate_poles, sample_field

FORCE_POINT = np.array([1.0, -0.5, 2.0])
FORCE = np.array([2.0, 1.0, -1.5])
CONFIG = SamplingConfig(n_planes=3, plane_spacing=1.5, angle_step_deg=60.0,
                        n_radii=2, radius_step=1.0)


def test_angle_step_must_divide_360():
    with pytest.raises(ValueError):
        SamplingConfig(angle_step_deg=70.0)


def test_sixty_degrees_gives_six_rays():
    assert CONFIG.n_rays == 6
    assert CONFIG.n_samples == 3 * 6 * 2


def test_poles_lie_on_equally_spaced_normal_planes():
    pole_set = generate_poles(CONFIG, FORCE_POINT, FORCE)
    s = (pole_set.poles - FORCE_POINT) @ pole_set.basis.u
    for k, expected in enumerate(pole_set.plane_offsets):
        assert np.abs(s[pole_set.plane_index == k] - expected).max() < 1e-12
    assert np.abs(np.diff(pole_set.plane_offsets) - CONFIG.plane_spacing).max() < 1e-12


def test_rays_are_separated_by_the_angle_step():
    pole_set = generate_poles(CONFIG, FORCE_POINT, FORCE)
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    radial = field.poles - field.feet
    angles = np.arctan2(radial @ pole_set.basis.v2, radial @ pole_set.basis.v1)
    expected = np.deg2rad(pole_set.ray_index * CONFIG.angle_step_deg)
    wrapped = np.angle(np.exp(1j * (angles - expected)))
    assert np.abs(wrapped).max() < 1e-12


def test_radial_distances_are_multiples_of_the_step_and_never_zero():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    expected = (field.radius_index + 1) * CONFIG.radius_step
    assert np.abs(field.radial_distance - expected).max() < 1e-12
    assert field.radial_distance.min() >= CONFIG.radius_step - 1e-12


def test_sampled_moments_match_direct_formula():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    direct = np.cross(FORCE_POINT - field.poles, FORCE)
    assert np.abs(field.moments - direct).max() == 0.0


def test_prev_v1_is_propagated_to_the_basis():
    basis = line_basis(FORCE)
    pole_set = generate_poles(CONFIG, FORCE_POINT, FORCE + 1e-3, prev_v1=basis.v1)
    assert np.linalg.norm(pole_set.basis.v1 - basis.v1) < 1e-2
