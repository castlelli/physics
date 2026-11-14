"""Numerical verification that the moment field is axisymmetric about the line of action.

Checks, to machine precision, on random poles:
1. M(O) · u = 0                       — M is normal to the axis;
2. |M(O)| = |F| · dist(O, axis)       — magnitude linear in the radial distance;
3. M(O + t·u) = M(O)                  — invariance under axial translation;
4. M(R_θ·O) = R_θ·M(O)                — equivariance under rotation about the axis.

(1)+(3)+(4) together are the axisymmetry stated in Capítulo 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from momentfield.core import axial_decomposition, line_basis, moment_field

DEFAULT_TOLERANCE = 1e-10


@dataclass(frozen=True)
class ProofReport:
    """Worst-case absolute errors of each verification, over all random poles."""

    max_axial_component: float  # max |M·u|
    max_magnitude_error: float  # max ||M| − |F|·|d||
    max_translation_error: float  # max |M(O + t·u) − M(O)|
    max_rotation_error: float  # max |M(R_θ·O) − R_θ·M(O)|
    tolerance: float
    n_poles: int

    @property
    def passed(self) -> bool:
        return (
            self.max_axial_component < self.tolerance
            and self.max_magnitude_error < self.tolerance
            and self.max_translation_error < self.tolerance
            and self.max_rotation_error < self.tolerance
        )


def rotation_about_axis(u: np.ndarray, theta: float) -> np.ndarray:
    """Rodrigues rotation matrix by θ about the unit vector u."""
    u = np.asarray(u, dtype=float)
    skew = np.array(
        [
            [0.0, -u[2], u[1]],
            [u[2], 0.0, -u[0]],
            [-u[1], u[0], 0.0],
        ]
    )
    return np.eye(3) + np.sin(theta) * skew + (1.0 - np.cos(theta)) * (skew @ skew)


def run_proofs(
    force_point: np.ndarray,
    force: np.ndarray,
    n_poles: int = 500,
    tolerance: float = DEFAULT_TOLERANCE,
    seed: int = 0,
) -> ProofReport:
    """Evaluate all four properties on random poles, shifts and angles."""
    force_point = np.asarray(force_point, dtype=float)
    force = np.asarray(force, dtype=float)
    u = line_basis(force).u
    force_norm = float(np.linalg.norm(force))

    rng = np.random.default_rng(seed)
    poles = force_point + rng.uniform(-5.0, 5.0, size=(n_poles, 3))
    moments = moment_field(poles, force_point, force)

    axial_component = np.abs(moments @ u)

    distance = axial_decomposition(poles, force_point, force).radial_distance
    magnitude_error = np.abs(np.linalg.norm(moments, axis=1) - force_norm * distance)

    shifts = rng.uniform(-10.0, 10.0, size=n_poles)
    translated = moment_field(poles + shifts[:, None] * u, force_point, force)
    translation_error = np.linalg.norm(translated - moments, axis=1)

    # rotate poles about the line of action (through P), compare rotated moments
    theta = float(rng.uniform(0.0, 2.0 * np.pi))
    rotation = rotation_about_axis(u, theta)
    rotated_poles = force_point + (poles - force_point) @ rotation.T
    rotation_error = np.linalg.norm(
        moment_field(rotated_poles, force_point, force) - moments @ rotation.T, axis=1
    )

    return ProofReport(
        max_axial_component=float(axial_component.max()),
        max_magnitude_error=float(magnitude_error.max()),
        max_translation_error=float(translation_error.max()),
        max_rotation_error=float(rotation_error.max()),
        tolerance=tolerance,
        n_poles=n_poles,
    )
