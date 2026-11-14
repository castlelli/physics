"""Pure math for the moment field of a single force.

M(O) = (P − O) ∧ F, with the decomposition (O − P) = s·u + d, u = F/|F|,
so that M(O) = F ∧ d — independent of the axial offset s (Capítulo 1).

No I/O, no matplotlib, no filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_ZERO_FORCE_TOL = 1e-12
_BASIS_CONTINUITY_TOL = 1e-8


@dataclass(frozen=True)
class LineBasis:
    """Orthonormal frame adapted to the line of action.

    ``u`` points along F; ``v1`` and ``v2`` span the plane normal to the line.
    """

    u: np.ndarray
    v1: np.ndarray
    v2: np.ndarray


@dataclass(frozen=True)
class AxialDecomposition:
    """Decomposition of poles relative to the line of action through P."""

    axial_offset: np.ndarray  # s = (O − P)·u, shape (N,)
    radial: np.ndarray  # d = (O − P) − s·u, shape (N, 3)
    radial_distance: np.ndarray  # |d|, shape (N,)
    foot: np.ndarray  # Q = P + s·u, foot of the perpendicular from O, shape (N, 3)


def line_basis(force: np.ndarray, prev_v1: np.ndarray | None = None) -> LineBasis:
    """Orthonormal basis (u, v1, v2) with u along the force.

    When ``prev_v1`` is given, v1 is obtained by Gram–Schmidt against the
    previous v1 instead of recomputed from scratch, so the frame stays
    continuous while F varies (avoids ray jumps near axis-alignment thresholds).
    """
    force = np.asarray(force, dtype=float)
    norm = float(np.linalg.norm(force))
    if norm < _ZERO_FORCE_TOL:
        raise ValueError("force must be non-zero: the line of action is undefined for F = 0")
    u = force / norm

    v1: np.ndarray | None = None
    if prev_v1 is not None:
        candidate = np.asarray(prev_v1, dtype=float)
        candidate = candidate - (candidate @ u) * u
        candidate_norm = float(np.linalg.norm(candidate))
        if candidate_norm > _BASIS_CONTINUITY_TOL:
            v1 = candidate / candidate_norm

    if v1 is None:
        # least-aligned coordinate axis gives the best-conditioned cross product
        least_aligned = np.eye(3)[int(np.argmin(np.abs(u)))]
        v1 = np.cross(u, least_aligned)
        v1 = v1 / np.linalg.norm(v1)

    v2 = np.cross(u, v1)
    return LineBasis(u=u, v1=v1, v2=v2)


def moment_field(poles: np.ndarray, force_point: np.ndarray, force: np.ndarray) -> np.ndarray:
    """Moment of F (applied at P) about each pole O: M(O) = (P − O) ∧ F (Capítulo 1)."""
    poles = np.atleast_2d(np.asarray(poles, dtype=float))
    force_point = np.asarray(force_point, dtype=float)
    force = np.asarray(force, dtype=float)
    return np.cross(force_point - poles, force)


def axial_decomposition(
    poles: np.ndarray, force_point: np.ndarray, force: np.ndarray
) -> AxialDecomposition:
    """Split (O − P) into axial offset s·u and radial component d ⊥ u."""
    poles = np.atleast_2d(np.asarray(poles, dtype=float))
    force_point = np.asarray(force_point, dtype=float)
    u = line_basis(force).u

    relative = poles - force_point
    axial_offset = relative @ u
    radial = relative - axial_offset[:, None] * u
    foot = force_point + axial_offset[:, None] * u
    return AxialDecomposition(
        axial_offset=axial_offset,
        radial=radial,
        radial_distance=np.linalg.norm(radial, axis=1),
        foot=foot,
    )
