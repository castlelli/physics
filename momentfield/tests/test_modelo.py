"""Numerical assertions on the moment field and the pole sampling (machine precision)."""

import numpy as np
import pytest

from codigo.modelo import (
    InputError,
    SamplingConfig,
    axial_decomposition,
    axial_section,
    line_basis,
    moment_field,
    normal_section,
    rotation_about_axis,
    sample_field,
)

FORCE_POINT = np.array([1.0, -0.5, 2.0])
FORCE = np.array([2.0, 1.0, -1.5])
RNG = np.random.default_rng(42)
POLES = FORCE_POINT + RNG.uniform(-5.0, 5.0, size=(200, 3))
CONFIG = SamplingConfig(n_planes=3, plane_spacing=1.5, angle_step_deg=60.0, n_radii=2, radius_step=1.0)


def test_moment_is_normal_to_the_axis():
    moments = moment_field(POLES, FORCE_POINT, FORCE)
    assert np.abs(moments @ line_basis(FORCE).u).max() < 1e-12 * np.linalg.norm(moments, axis=1).max()


def test_magnitude_is_linear_in_the_distance_to_the_axis():
    moments = moment_field(POLES, FORCE_POINT, FORCE)
    expected = np.linalg.norm(FORCE) * axial_decomposition(POLES, FORCE_POINT, FORCE).radial_distance
    assert np.abs(np.linalg.norm(moments, axis=1) - expected).max() < 1e-12 * expected.max()


def test_moment_equals_force_wedge_radial_part():
    # M(O) = F ∧ d (Capítulo 1)
    radial = axial_decomposition(POLES, FORCE_POINT, FORCE).radial
    moments = moment_field(POLES, FORCE_POINT, FORCE)
    assert np.abs(moments - np.cross(FORCE, radial)).max() < 1e-12 * np.abs(moments).max()


def test_invariance_under_translation_along_the_axis():
    u = line_basis(FORCE).u
    shifts = RNG.uniform(-10.0, 10.0, size=len(POLES))
    original = moment_field(POLES, FORCE_POINT, FORCE)
    translated = moment_field(POLES + shifts[:, None] * u, FORCE_POINT, FORCE)
    assert np.linalg.norm(translated - original, axis=1).max() < 1e-12 * np.linalg.norm(original, axis=1).max()


@pytest.mark.parametrize("theta", RNG.uniform(0.0, 2.0 * np.pi, size=5).tolist())
def test_rotational_equivariance(theta):
    rotation = rotation_about_axis(line_basis(FORCE).u, theta)
    lhs = moment_field(FORCE_POINT + (POLES - FORCE_POINT) @ rotation.T, FORCE_POINT, FORCE)
    rhs = moment_field(POLES, FORCE_POINT, FORCE) @ rotation.T
    assert np.linalg.norm(lhs - rhs, axis=1).max() < 1e-12 * np.linalg.norm(rhs, axis=1).max()


def test_moment_on_the_axis_is_zero_without_nan():
    on_axis = FORCE_POINT + np.outer(np.linspace(-3.0, 3.0, 7), line_basis(FORCE).u)
    moments = moment_field(on_axis, FORCE_POINT, FORCE)
    assert np.all(np.isfinite(moments))
    assert np.linalg.norm(moments, axis=1).max() < 1e-12 * np.linalg.norm(FORCE)


def test_zero_force_is_rejected():
    with pytest.raises(InputError):
        line_basis(np.zeros(3))


def test_basis_is_orthonormal_and_right_handed():
    b = line_basis(FORCE)
    matrix = np.stack([b.u, b.v1, b.v2])
    assert np.abs(matrix @ matrix.T - np.eye(3)).max() < 1e-12
    assert np.abs(np.cross(b.u, b.v1) - b.v2).max() < 1e-12


def test_basis_stays_continuous_under_a_small_change_of_force():
    b = line_basis(FORCE)
    nudged = line_basis(FORCE + np.array([1e-3, -2e-3, 1e-3]), prev_v1=b.v1)
    assert np.linalg.norm(nudged.v1 - b.v1) < 1e-2


def test_foot_is_the_orthogonal_projection_on_the_line_of_action():
    d = axial_decomposition(POLES, FORCE_POINT, FORCE)
    u = line_basis(FORCE).u
    to_foot = d.foot - FORCE_POINT
    assert np.abs(np.cross(to_foot, u)).max() < 1e-12 * np.abs(to_foot).max()
    assert np.abs((POLES - d.foot) @ u).max() < 1e-12 * np.abs(POLES).max()


def test_angle_step_must_divide_360():
    with pytest.raises(InputError):
        SamplingConfig(angle_step_deg=70.0)


def test_sixty_degrees_gives_six_rays():
    assert CONFIG.n_rays == 6
    assert CONFIG.n_samples == 3 * 6 * 2


def test_poles_lie_on_equally_spaced_normal_planes():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    s = (field.poles - FORCE_POINT) @ field.basis.u
    for k, expected in enumerate(field.plane_offsets):
        assert np.abs(s[field.plane_index == k] - expected).max() < 1e-12
    assert np.abs(np.diff(field.plane_offsets) - CONFIG.plane_spacing).max() < 1e-12


def test_rays_are_separated_by_the_angle_step():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    radial = field.poles - field.feet
    angles = np.arctan2(radial @ field.basis.v2, radial @ field.basis.v1)
    expected = np.deg2rad(field.ray_index * CONFIG.angle_step_deg)
    assert np.abs(np.angle(np.exp(1j * (angles - expected)))).max() < 1e-12


def test_radial_distances_are_multiples_of_the_step_and_never_zero():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    assert np.abs(field.radial_distance - (field.radius_index + 1) * CONFIG.radius_step).max() < 1e-12
    assert field.radial_distance.min() >= CONFIG.radius_step - 1e-12


def test_sampled_moments_match_the_direct_formula():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    assert np.abs(field.moments - np.cross(FORCE_POINT - field.poles, FORCE)).max() == 0.0


def test_prev_v1_reaches_the_sampled_basis():
    b = line_basis(FORCE)
    field = sample_field(CONFIG, FORCE_POINT, FORCE + 1e-3, prev_v1=b.v1)
    assert np.linalg.norm(field.basis.v1 - b.v1) < 1e-2


def test_normal_section_is_one_plane():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    mask = normal_section(field)
    assert mask.sum() == CONFIG.n_rays * CONFIG.n_radii
    assert np.ptp(field.axial_offset[mask]) < 1e-12


def test_axial_section_holds_the_poles_in_the_plane_of_the_axis_and_v1():
    field = sample_field(CONFIG, FORCE_POINT, FORCE)
    mask = axial_section(field)
    assert mask.sum() == 2 * CONFIG.n_planes * CONFIG.n_radii
    assert np.abs((field.poles[mask] - FORCE_POINT) @ field.basis.v2).max() < 1e-12


def test_axial_section_with_odd_ray_count_keeps_one_side():
    field = sample_field(SamplingConfig(angle_step_deg=120.0), FORCE_POINT, FORCE)
    assert axial_section(field).sum() == field.config.n_planes * field.config.n_radii
