"""Physical assertions on the reduction, to machine precision, for random systems and every ready case."""

import numpy as np
import pytest

from codigo.casos import CASES
from codigo.modelo import (
    COUPLE,
    FORCE_COUPLE,
    NULL,
    SINGLE_FORCE,
    Box,
    InputError,
    System,
    moment_about,
    reduce,
)

RNG = np.random.default_rng(7)


def random_system(n: int) -> System:
    return System(RNG.normal(size=(n, 3)), RNG.uniform(0, 2, size=(n, 3)), RNG.uniform(0, 2, size=3),
                  RNG.uniform(0, 2, size=3), RNG.normal(size=3))


SYSTEMS = [random_system(n) for n in (1, 2, 3, 5, 8)]


@pytest.mark.parametrize("system", SYSTEMS)
def test_transport_of_moments_matches_the_direct_sum(system):
    r = reduce(system)
    direct = moment_about(system, system.pole_a)
    assert np.abs(r.moment_a - direct).max() < 1e-12 * max(1.0, np.abs(direct).max())


@pytest.mark.parametrize("system", SYSTEMS)
def test_invariant_is_the_same_at_every_pole(system):
    r = reduce(system)
    for pole in RNG.uniform(-3, 3, size=(20, 3)):
        assert abs(r.resultant @ moment_about(system, pole) - r.invariant) < 1e-12 * r.force_scale ** 2 * 10


@pytest.mark.parametrize("system", SYSTEMS)
def test_moment_on_the_central_axis_is_parallel_to_r_and_minimal(system):
    r = reduce(system)
    assert r.has_central_axis
    for t in (-2.0, 0.0, 1.5):
        on_axis = moment_about(system, r.axis_point + t * r.axis_direction)
        assert np.abs(on_axis - r.minimum_moment).max() < 1e-12 * r.force_scale * 10
    # |M(P)|² = |M_E|² + |R|² d², d the distance from P to the central axis
    for pole in RNG.uniform(-3, 3, size=(20, 3)):
        offset = pole - r.axis_point
        d2 = offset @ offset - (offset @ r.axis_direction) ** 2
        m = moment_about(system, pole)
        expected = r.minimum_moment @ r.minimum_moment + (r.resultant @ r.resultant) * d2
        assert abs(m @ m - expected) < 1e-10 * max(1.0, expected)


@pytest.mark.parametrize("system", SYSTEMS)
def test_axis_torque_is_the_projection_of_m_a_on_u(system):
    r = reduce(system)
    assert abs(np.linalg.norm(r.unit_u) - 1) < 1e-15
    assert abs(r.axis_torque - r.moment_a @ system.u / np.linalg.norm(system.u)) < 1e-12 * max(1.0, abs(r.axis_torque))


@pytest.mark.parametrize("key", sorted(CASES))
def test_every_case_has_its_category_and_shape(key):
    case = CASES[key]
    r = reduce(case.system())
    assert r.category == case.expected
    assert r.shape == case.expected_shape
    assert all(case.system().box.contains(p) for p in case.system().points)


def crosses_box(point, direction, size, tol=1e-9) -> bool:
    """Whether the line point + t·direction meets the box [0, size] (slab test)."""
    lo, hi = -np.inf, np.inf
    for i in range(3):
        if abs(direction[i]) < 1e-12:
            if not -tol <= point[i] <= size[i] + tol:
                return False
        else:
            t1, t2 = (-tol - point[i]) / direction[i], (size[i] + tol - point[i]) / direction[i]
            lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
    return lo <= hi


@pytest.mark.parametrize("key", sorted(CASES))
def test_the_central_axis_of_every_example_crosses_the_box(key):
    system = CASES[key].system()
    r = reduce(system)
    if r.has_central_axis:
        size = np.array([system.box.a, system.box.b, system.box.c])
        assert crosses_box(r.axis_point, r.axis_direction, size)


def test_the_cases_cover_the_four_categories_and_the_three_shapes():
    categories = {c.expected for c in CASES.values()}
    assert categories == {NULL, COUPLE, SINGLE_FORCE, FORCE_COUPLE}
    single = [c.expected_shape for c in CASES.values() if c.expected == SINGLE_FORCE]
    assert {s for shape in single for s in shape} >= {"parallel", "concurrent", "coplanar"}


def test_single_force_has_zero_minimum_moment_and_the_axis_is_its_line_of_action():
    # n = 1: the central axis is the force's own line of action, with no singularity
    system = CASES["uma_forca"].system()
    r = reduce(system)
    assert np.abs(r.minimum_moment).max() < 1e-15
    to_point = system.points[0] - r.axis_point
    assert np.linalg.norm(np.cross(to_point, r.axis_direction)) < 1e-12


def test_couple_has_the_same_moment_at_every_pole_and_no_axis():
    system = CASES["binario_duplo"].system()
    r = reduce(system)
    assert not r.has_central_axis and r.minimum_moment is None
    assert np.abs(r.moment_q - r.moment_a).max() < 1e-12


def test_null_system_has_zero_everything():
    r = reduce(CASES["nulo_concorrentes"].system())
    assert r.category == NULL
    assert np.abs(r.resultant).max() == 0 and np.abs(r.moment_q).max() < 1e-12 and r.axis_torque == 0


def test_tolerance_scales_with_the_data():
    # the same couple in millinewtons and in meganewtons stays a couple
    base = CASES["binario_arestas"]
    for k in (1e-3, 1e6):
        system = System(np.array(base.forces) * k, np.array(base.points), np.array(base.pole_q),
                        np.array(base.pole_a), np.array(base.u))
        assert reduce(system).category == COUPLE


def test_bad_inputs_are_rejected():
    with pytest.raises(InputError):
        System(np.zeros((1, 3)), np.zeros((1, 3)), np.zeros(3), np.zeros(3), np.zeros(3))  # u = 0
    with pytest.raises(InputError):
        System(np.zeros((2, 3)), np.zeros((1, 3)), np.zeros(3), np.zeros(3), np.ones(3))  # points missing
    with pytest.raises(InputError):
        Box(1.0, 0.0, 1.0)


def test_points_outside_the_box_are_detected():
    box = Box(2, 1.5, 1)
    assert box.contains([2, 1.5, 1]) and box.contains([0, 0, 0])
    assert not box.contains([2.1, 0, 0])
