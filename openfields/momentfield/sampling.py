"""Generation of poles O on planes normal to the line of action.

Poles are arranged as planes × rays × radii:
- planes normal to the line of action, equally spaced along it;
- within each plane, rays Q → O separated by ``angle_step_deg`` (60° → 6 rays);
- along each ray, equally spaced radii starting at ``radius_step`` (never on
  the axis itself, where d = 0 and the radial direction is undefined).

No I/O, no matplotlib, no filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from momentfield.core import LineBasis, axial_decomposition, line_basis, moment_field


@dataclass(frozen=True)
class SamplingConfig:
    """Layout of the sampled poles around the line of action."""

    n_planes: int = 3
    plane_spacing: float = 1.5
    angle_step_deg: float = 60.0
    n_radii: int = 2
    radius_step: float = 1.0

    def __post_init__(self) -> None:
        if self.n_planes < 1:
            raise ValueError("n_planes must be >= 1")
        if self.plane_spacing <= 0:
            raise ValueError("plane_spacing must be > 0")
        if self.n_radii < 1:
            raise ValueError("n_radii must be >= 1")
        if self.radius_step <= 0:
            raise ValueError("radius_step must be > 0")
        if self.angle_step_deg <= 0 or 360.0 % self.angle_step_deg != 0:
            raise ValueError("angle_step_deg must divide 360 exactly")

    @property
    def n_rays(self) -> int:
        return round(360.0 / self.angle_step_deg)

    @property
    def n_samples(self) -> int:
        return self.n_planes * self.n_rays * self.n_radii


@dataclass(frozen=True)
class PoleSet:
    """Sampled poles with the indices needed to filter sections downstream."""

    poles: np.ndarray  # (N, 3)
    plane_index: np.ndarray  # (N,) int
    ray_index: np.ndarray  # (N,) int
    radius_index: np.ndarray  # (N,) int
    basis: LineBasis
    plane_offsets: np.ndarray  # s value of each plane, (n_planes,)


@dataclass(frozen=True)
class SampledField:
    """Poles plus the moment field evaluated on them — the full render/export payload."""

    config: SamplingConfig
    force_point: np.ndarray  # P, (3,)
    force: np.ndarray  # F, (3,)
    basis: LineBasis
    poles: np.ndarray  # O, (N, 3)
    moments: np.ndarray  # M(O), (N, 3)
    feet: np.ndarray  # Q, (N, 3)
    axial_offset: np.ndarray  # s, (N,)
    radial_distance: np.ndarray  # |d|, (N,)
    plane_index: np.ndarray  # (N,) int
    ray_index: np.ndarray  # (N,) int
    radius_index: np.ndarray  # (N,) int


def generate_poles(
    config: SamplingConfig,
    force_point: np.ndarray,
    force: np.ndarray,
    prev_v1: np.ndarray | None = None,
) -> PoleSet:
    """Poles O = P + s·u + r·(cosθ·v1 + sinθ·v2), fully vectorized."""
    force_point = np.asarray(force_point, dtype=float)
    basis = line_basis(force, prev_v1=prev_v1)

    # planes equally spaced along the axis, centered on P
    plane_offsets = (np.arange(config.n_planes) - (config.n_planes - 1) / 2.0) * config.plane_spacing
    angles = np.deg2rad(np.arange(config.n_rays) * config.angle_step_deg)
    radii = np.arange(1, config.n_radii + 1) * config.radius_step

    plane_idx, ray_idx, radius_idx = (
        grid.ravel()
        for grid in np.meshgrid(
            np.arange(config.n_planes),
            np.arange(config.n_rays),
            np.arange(config.n_radii),
            indexing="ij",
        )
    )
    s = plane_offsets[plane_idx]
    theta = angles[ray_idx]
    r = radii[radius_idx]

    poles = (
        force_point
        + s[:, None] * basis.u
        + (r * np.cos(theta))[:, None] * basis.v1
        + (r * np.sin(theta))[:, None] * basis.v2
    )
    return PoleSet(
        poles=poles,
        plane_index=plane_idx,
        ray_index=ray_idx,
        radius_index=radius_idx,
        basis=basis,
        plane_offsets=plane_offsets,
    )


def sample_field(
    config: SamplingConfig,
    force_point: np.ndarray,
    force: np.ndarray,
    prev_v1: np.ndarray | None = None,
) -> SampledField:
    """Generate poles and evaluate M, Q, s, |d| on them."""
    force_point = np.asarray(force_point, dtype=float)
    force = np.asarray(force, dtype=float)
    pole_set = generate_poles(config, force_point, force, prev_v1=prev_v1)
    moments = moment_field(pole_set.poles, force_point, force)
    decomposition = axial_decomposition(pole_set.poles, force_point, force)
    return SampledField(
        config=config,
        force_point=force_point,
        force=force,
        basis=pole_set.basis,
        poles=pole_set.poles,
        moments=moments,
        feet=decomposition.foot,
        axial_offset=decomposition.axial_offset,
        radial_distance=decomposition.radial_distance,
        plane_index=pole_set.plane_index,
        ray_index=pole_set.ray_index,
        radius_index=pole_set.radius_index,
    )
