"""Reduction of a system of forces on a rigid body.

R = Σ F_i, M_Q = Σ (P_i − Q) ∧ F_i, transport M_A = M_Q + (Q − A) ∧ R, scalar invariant I = R·M,
central axis through E₀ = Q + (R ∧ M_Q)/|R|² along R, minimum moment M_E = (I/|R|²) R.

No I/O, no matplotlib. docs/wrench/js/model.js repeats this module; tests/test_paridade.py checks
both against the same fixture.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Relative tolerance of every "is it zero?" decision; scales come from the data (see Reduction).
EPS = 1e-9

NULL = "null"
COUPLE = "couple"
SINGLE_FORCE = "single_force"
FORCE_COUPLE = "force_couple"

PARALLEL = "parallel"
CONCURRENT = "concurrent"
COPLANAR = "coplanar"


class InputError(ValueError):
    """Input the reduction cannot be computed from."""


@dataclass(frozen=True)
class Box:
    """Rectangular box with one corner at O and edges a, b, c along x, y, z."""

    a: float = 2.0
    b: float = 1.5
    c: float = 1.0

    def __post_init__(self) -> None:
        if min(self.a, self.b, self.c) <= 0:
            raise InputError("as arestas da caixa devem ser positivas")

    def contains(self, point: np.ndarray, tol: float = 1e-9) -> bool:
        p = np.asarray(point, dtype=float)
        size = np.array([self.a, self.b, self.c])
        return bool(np.all(p >= -tol * size) and np.all(p <= size * (1 + tol)))


@dataclass(frozen=True)
class System:
    """The statement's input: n ≥ 1 forces F_i at P_i, poles Q and A, a direction u."""

    forces: np.ndarray  # (n, 3)
    points: np.ndarray  # (n, 3)
    pole_q: np.ndarray  # (3,)
    pole_a: np.ndarray  # (3,)
    u: np.ndarray  # (3,), normalised by reduce()
    box: Box = field(default_factory=Box)

    def __post_init__(self) -> None:
        forces = np.atleast_2d(np.asarray(self.forces, dtype=float))
        points = np.atleast_2d(np.asarray(self.points, dtype=float))
        if forces.shape[0] < 1 or forces.shape[1:] != (3,):
            raise InputError("é preciso ao menos uma força com 3 componentes")
        if points.shape != forces.shape:
            raise InputError("cada força precisa de um ponto de aplicação")
        object.__setattr__(self, "forces", forces)
        object.__setattr__(self, "points", points)
        for name in ("pole_q", "pole_a", "u"):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.shape != (3,):
                raise InputError(f"{name} precisa de 3 componentes")
            object.__setattr__(self, name, value)
        if not np.all(np.isfinite(forces)) or not np.all(np.isfinite(points)):
            raise InputError("os dados precisam ser números finitos")
        if np.linalg.norm(self.u) == 0:
            raise InputError("o versor u não pode ser nulo")

    @property
    def n(self) -> int:
        return self.forces.shape[0]


@dataclass(frozen=True)
class Reduction:
    """Every output of the statement, items a) to g)."""

    resultant: np.ndarray  # a) R
    moment_q: np.ndarray  # b) M_Q
    moment_a: np.ndarray  # c) M_A
    unit_u: np.ndarray  # û = u/|u|
    axis_torque: float  # d) M_A·û, the torque about the axis through A along û
    invariant: float  # e) I = R·M_Q
    category: str  # f) NULL, COUPLE, SINGLE_FORCE or FORCE_COUPLE
    shape: tuple[str, ...]  # PARALLEL, CONCURRENT, COPLANAR when they hold (n ≥ 2)
    axis_point: np.ndarray | None  # g) E₀, the point of the central axis nearest to Q
    axis_direction: np.ndarray | None  # g) R/|R|
    minimum_moment: np.ndarray | None  # g) M_E
    force_scale: float  # S = Σ|F_i|
    length_scale: float  # L = largest distance between P_i, Q and A

    @property
    def has_central_axis(self) -> bool:
        return self.axis_point is not None

    @property
    def axis_torque_vector(self) -> np.ndarray:
        return self.axis_torque * self.unit_u


def moment_about(system: System, pole: np.ndarray) -> np.ndarray:
    """Σ (P_i − pole) ∧ F_i, summed directly over the forces."""
    return np.cross(system.points - np.asarray(pole, dtype=float), system.forces).sum(axis=0)


def length_scale(system: System) -> float:
    points = np.vstack([system.points, system.pole_q, system.pole_a])
    largest = float(np.max(np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)))
    return largest if largest > 0 else 1.0


def classify(resultant: np.ndarray, moment: np.ndarray, invariant: float, force_scale: float, length: float) -> str:
    """Category of the system from R, the moment at any pole and I (tolerances relative to the data)."""
    r_zero = np.linalg.norm(resultant) <= EPS * force_scale
    m_zero = np.linalg.norm(moment) <= EPS * force_scale * length
    if r_zero:
        return NULL if m_zero else COUPLE
    i_zero = abs(invariant) <= EPS * np.linalg.norm(resultant) * force_scale * length
    return SINGLE_FORCE if i_zero else FORCE_COUPLE


def force_shape(system: System, force_scale: float, length: float) -> tuple[str, ...]:
    """Which of parallel, concurrent and coplanar the lines of action are (only for n ≥ 2 non-zero forces)."""
    norms = np.linalg.norm(system.forces, axis=1)
    active = norms > EPS * force_scale
    if active.sum() < 2:
        return ()
    directions = system.forces[active] / norms[active, None]
    points = system.points[active]
    shapes = []

    parallel = bool(np.all(np.linalg.norm(np.cross(directions, directions[0]), axis=1) <= EPS))
    if parallel:
        shapes.append(PARALLEL)
    else:
        # point nearest to every line in the least-squares sense: Σ (I − d dᵀ)(X − P) = 0
        projectors = np.eye(3)[None, :, :] - directions[:, :, None] * directions[:, None, :]
        matrix = projectors.sum(axis=0)
        rhs = np.einsum("nij,nj->i", projectors, points)
        meet = np.linalg.solve(matrix, rhs)
        offsets = np.einsum("nij,nj->ni", projectors, meet - points)
        if np.max(np.linalg.norm(offsets, axis=1)) <= EPS * length:
            shapes.append(CONCURRENT)

    # every line lies in one plane: the points P_i and P_i + L·d_i all lie in the plane spanned by the
    # two of them (seen from the first) with the largest cross product. A direct test, so model.js
    # can repeat it decision for decision.
    cloud = np.vstack([points, points + length * directions])
    spokes = cloud[1:] - cloud[0]
    crosses = np.cross(spokes[:, None, :], spokes[None, :, :])
    sizes = np.linalg.norm(crosses, axis=2)
    j, k = np.unravel_index(int(np.argmax(sizes)), sizes.shape)
    if sizes[j, k] <= EPS * length * length:
        shapes.append(COPLANAR)  # every point on one line: any plane through it holds them all
    else:
        normal = crosses[j, k] / sizes[j, k]
        if np.max(np.abs(spokes @ normal)) <= EPS * length:
            shapes.append(COPLANAR)
    return tuple(shapes)


def reduce(system: System) -> Reduction:
    """Items a) to g) of the statement."""
    resultant = system.forces.sum(axis=0)
    moment_q = moment_about(system, system.pole_q)
    moment_a = moment_q + np.cross(system.pole_q - system.pole_a, resultant)  # transport of moments
    unit_u = system.u / np.linalg.norm(system.u)
    invariant = float(resultant @ moment_q)
    force_scale = float(np.linalg.norm(system.forces, axis=1).sum())
    length = length_scale(system)
    category = classify(resultant, moment_q, invariant, force_scale, length)

    axis_point = axis_direction = minimum_moment = None
    if category in (SINGLE_FORCE, FORCE_COUPLE):
        r2 = float(resultant @ resultant)
        axis_point = system.pole_q + np.cross(resultant, moment_q) / r2
        axis_direction = resultant / np.sqrt(r2)
        minimum_moment = (invariant / r2) * resultant

    return Reduction(
        resultant=resultant,
        moment_q=moment_q,
        moment_a=moment_a,
        unit_u=unit_u,
        axis_torque=float(moment_a @ unit_u),
        invariant=invariant,
        category=category,
        shape=force_shape(system, force_scale, length),
        axis_point=axis_point,
        axis_direction=axis_direction,
        minimum_moment=minimum_moment,
        force_scale=force_scale,
        length_scale=length,
    )
