"""Numerical assertions on the moment field math (machine precision)."""

import numpy as np
import pytest

from momentfield.core import axial_decomposition, line_basis, moment_field
from momentfield.proofs import rotation_about_axis

FORCE_POINT = np.array([1.0, -0.5, 2.0])
FORCE = np.array([2.0, 1.0, -1.5])
RNG = np.random.default_rng(42)
POLES = FORCE_POINT + RNG.uniform(-5.0, 5.0, size=(200, 3))


def test_moment_is_normal_to_the_axis():
    moments = moment_field(POLES, FORCE_POINT, FORCE)
    u = line_basis(FORCE).u
    assert np.abs(moments @ u).max() < 1e-12 * np.linalg.norm(moments, axis=1).max()


def test_magnitude_is_linear_in_radial_distance():
    moments = moment_field(POLES, FORCE_POINT, FORCE)
    distance = axial_decomposition(POLES, FORCE_POINT, FORCE).radial_distance
    expected = np.linalg.norm(FORCE) * distance
    assert np.abs(np.linalg.norm(moments, axis=1) - expected).max() < 1e-12 * expected.max()


def test_invariance_under_axial_translation():
    u = line_basis(FORCE).u
    shifts = RNG.uniform(-10.0, 10.0, size=len(POLES))
    original = moment_field(POLES, FORCE_POINT, FORCE)
    translated = moment_field(POLES + shifts[:, None] * u, FORCE_POINT, FORCE)
    scale = np.linalg.norm(original, axis=1).max()
    assert np.linalg.norm(translated - original, axis=1).max() < 1e-12 * scale


@pytest.mark.parametrize("theta", RNG.uniform(0.0, 2.0 * np.pi, size=5).tolist())
def test_rotational_equivariance(theta):
    u = line_basis(FORCE).u
    rotation = rotation_about_axis(u, theta)
    rotated_poles = FORCE_POINT + (POLES - FORCE_POINT) @ rotation.T
    lhs = moment_field(rotated_poles, FORCE_POINT, FORCE)
    rhs = moment_field(POLES, FORCE_POINT, FORCE) @ rotation.T
    scale = np.linalg.norm(rhs, axis=1).max()
    assert np.linalg.norm(lhs - rhs, axis=1).max() < 1e-12 * scale


def test_moment_on_the_axis_is_zero_without_nan():
    u = line_basis(FORCE).u
    on_axis = FORCE_POINT + np.outer(np.linspace(-3.0, 3.0, 7), u)
    moments = moment_field(on_axis, FORCE_POINT, FORCE)
    assert np.all(np.isfinite(moments))
    assert np.linalg.norm(moments, axis=1).max() < 1e-12 * np.linalg.norm(FORCE)


def test_zero_force_raises():
    with pytest.raises(ValueError):
        line_basis(np.zeros(3))


def test_basis_is_orthonormal_and_right_handed():
    basis = line_basis(FORCE)
    matrix = np.stack([basis.u, basis.v1, basis.v2])
    assert np.abs(matrix @ matrix.T - np.eye(3)).max() < 1e-12
    assert np.abs(np.cross(basis.u, basis.v1) - basis.v2).max() < 1e-12


def test_basis_continuity_under_small_force_change():
    basis = line_basis(FORCE)
    nudged = line_basis(FORCE + np.array([1e-3, -2e-3, 1e-3]), prev_v1=basis.v1)
    assert np.linalg.norm(nudged.v1 - basis.v1) < 1e-2


def test_foot_is_the_orthogonal_projection():
    decomposition = axial_decomposition(POLES, FORCE_POINT, FORCE)
    u = line_basis(FORCE).u
    # Q on the line of action, and O − Q perpendicular to it
    to_foot = decomposition.foot - FORCE_POINT
    assert np.abs(np.cross(to_foot, u)).max() < 1e-12 * np.abs(to_foot).max()
    assert np.abs((POLES - decomposition.foot) @ u).max() < 1e-12 * np.abs(POLES).max()
