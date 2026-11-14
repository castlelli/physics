"""Numerical proof that the moment field is axisymmetric about the line of action.

On random poles, to machine precision:
1. M(O)·u = 0                    M is normal to the axis;
2. |M(O)| = |F|·dist(O, axis)    magnitude linear in the distance to the axis;
3. M(O + t·u) = M(O)             invariance under translation along the axis;
4. M(R_θ·O) = R_θ·M(O)           equivariance under rotation about the axis.

(1), (3) and (4) together are the axisymmetry stated in Capítulo 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .modelo import axial_decomposition, line_basis, moment_field, rotation_about_axis

RELATIVE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ProofReport:
    """Worst errors of each property, relative to the largest |M| over the random poles."""

    max_axial_component: float  # max |M·u|
    max_magnitude_error: float  # max ||M| − |F|·|d||
    max_translation_error: float  # max |M(O + t·u) − M(O)|
    max_rotation_error: float  # max |M(R·O) − R·M(O)|
    moment_scale: float  # max |M|, the scale the errors are compared to
    n_poles: int

    def relative(self) -> dict[str, float]:
        scale = self.moment_scale or 1.0
        return {
            "axial_component": self.max_axial_component / scale,
            "magnitude": self.max_magnitude_error / scale,
            "translation": self.max_translation_error / scale,
            "rotation": self.max_rotation_error / scale,
        }

    @property
    def passed(self) -> bool:
        return all(value < RELATIVE_TOLERANCE for value in self.relative().values())


def run_proofs(force_point: np.ndarray, force: np.ndarray, n_poles: int = 500, seed: int = 0) -> ProofReport:
    """Evaluate the four properties on random poles, shifts and one random angle."""
    force_point = np.asarray(force_point, dtype=float)
    force = np.asarray(force, dtype=float)
    u = line_basis(force).u
    rng = np.random.default_rng(seed)

    poles = force_point + rng.uniform(-5.0, 5.0, size=(n_poles, 3))
    moments = moment_field(poles, force_point, force)
    distance = axial_decomposition(poles, force_point, force).radial_distance

    shifts = rng.uniform(-10.0, 10.0, size=n_poles)
    translated = moment_field(poles + shifts[:, None] * u, force_point, force)

    # rotate the poles about the line of action (through P) and compare with the rotated moments
    rotation = rotation_about_axis(u, float(rng.uniform(0.0, 2.0 * np.pi)))
    rotated = moment_field(force_point + (poles - force_point) @ rotation.T, force_point, force)

    return ProofReport(
        max_axial_component=float(np.abs(moments @ u).max()),
        max_magnitude_error=float(np.abs(np.linalg.norm(moments, axis=1) - np.linalg.norm(force) * distance).max()),
        max_translation_error=float(np.linalg.norm(translated - moments, axis=1).max()),
        max_rotation_error=float(np.linalg.norm(rotated - moments @ rotation.T, axis=1).max()),
        moment_scale=float(np.linalg.norm(moments, axis=1).max()),
        n_poles=n_poles,
    )
