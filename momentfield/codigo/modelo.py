"""Moment field of a single force: pure math and pole sampling.

M(O) = (P − O) ∧ F. With u = F/|F| and (O − P) = s·u + d, d ⊥ u:
M(O) = −(s·u + d) ∧ F = F ∧ d, independent of the axial offset s (Capítulo 1).

No I/O, no matplotlib, no filesystem access. docs/momentfield/js/model.js repeats this
module line by line; tests/test_paridade.py checks both against the same fixture.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ZERO_FORCE_TOL = 1e-12
BASIS_CONTINUITY_TOL = 1e-8


class InputError(ValueError):
    """Input the field cannot be built from (F = 0, an angle step that does not divide 360, ...)."""


@dataclass(frozen=True)
class LineBasis:
    """Orthonormal frame adapted to the line of action: u along F, v1 and v2 span the normal plane."""

    u: np.ndarray
    v1: np.ndarray
    v2: np.ndarray


@dataclass(frozen=True)
class AxialDecomposition:
    """Poles relative to the line of action through P."""

    axial_offset: np.ndarray  # s = (O − P)·u, (N,)
    radial: np.ndarray  # d = (O − P) − s·u, (N, 3)
    radial_distance: np.ndarray  # |d|, (N,)
    foot: np.ndarray  # Q = P + s·u, foot of the perpendicular from O, (N, 3)


def line_basis(force: np.ndarray, prev_v1: np.ndarray | None = None) -> LineBasis:
    """Orthonormal basis (u, v1, v2), right-handed, with u along the force.

    With ``prev_v1``, v1 comes from Gram–Schmidt against the previous v1 instead of being
    recomputed, so the frame stays continuous while F varies (no ray jumps when dragging).
    """
    force = np.asarray(force, dtype=float)
    norm = float(np.linalg.norm(force))
    if norm < ZERO_FORCE_TOL:
        raise InputError("a força não pode ser nula: sem força não há linha de ação")
    u = force / norm

    v1: np.ndarray | None = None
    if prev_v1 is not None:
        candidate = np.asarray(prev_v1, dtype=float)
        candidate = candidate - (candidate @ u) * u
        candidate_norm = float(np.linalg.norm(candidate))
        if candidate_norm > BASIS_CONTINUITY_TOL:
            v1 = candidate / candidate_norm

    if v1 is None:
        # least-aligned coordinate axis gives the best-conditioned cross product
        least_aligned = np.eye(3)[int(np.argmin(np.abs(u)))]
        v1 = np.cross(u, least_aligned)
        v1 = v1 / np.linalg.norm(v1)

    return LineBasis(u=u, v1=v1, v2=np.cross(u, v1))


def moment_field(poles: np.ndarray, force_point: np.ndarray, force: np.ndarray) -> np.ndarray:
    """Moment of F, applied at P, about each pole O: M(O) = (P − O) ∧ F (Capítulo 1)."""
    poles = np.atleast_2d(np.asarray(poles, dtype=float))
    return np.cross(np.asarray(force_point, dtype=float) - poles, np.asarray(force, dtype=float))


def axial_decomposition(poles: np.ndarray, force_point: np.ndarray, force: np.ndarray) -> AxialDecomposition:
    """Split (O − P) into the axial part s·u and the radial part d ⊥ u."""
    poles = np.atleast_2d(np.asarray(poles, dtype=float))
    force_point = np.asarray(force_point, dtype=float)
    u = line_basis(force).u
    relative = poles - force_point
    axial_offset = relative @ u
    radial = relative - axial_offset[:, None] * u
    return AxialDecomposition(
        axial_offset=axial_offset,
        radial=radial,
        radial_distance=np.linalg.norm(radial, axis=1),
        foot=force_point + axial_offset[:, None] * u,
    )


def rotation_about_axis(u: np.ndarray, theta: float) -> np.ndarray:
    """Rodrigues rotation matrix by θ about the unit vector u."""
    u = np.asarray(u, dtype=float)
    skew = np.array([[0.0, -u[2], u[1]], [u[2], 0.0, -u[0]], [-u[1], u[0], 0.0]])
    return np.eye(3) + np.sin(theta) * skew + (1.0 - np.cos(theta)) * (skew @ skew)


@dataclass(frozen=True)
class SamplingConfig:
    """Layout of the poles: planes normal to the line of action × rays × radii."""

    n_planes: int = 3
    plane_spacing: float = 1.5
    angle_step_deg: float = 60.0
    n_radii: int = 2
    radius_step: float = 1.0

    def __post_init__(self) -> None:
        if self.n_planes < 1:
            raise InputError("é preciso ao menos 1 plano")
        if self.plane_spacing <= 0:
            raise InputError("o espaçamento entre planos deve ser positivo")
        if self.n_radii < 1:
            raise InputError("é preciso ao menos 1 distância por raio")
        if self.radius_step <= 0:
            raise InputError("o passo radial deve ser positivo")
        if self.angle_step_deg <= 0 or 360.0 % self.angle_step_deg != 0:
            raise InputError("o passo angular deve dividir 360° exatamente")

    @property
    def n_rays(self) -> int:
        return round(360.0 / self.angle_step_deg)

    @property
    def n_samples(self) -> int:
        return self.n_planes * self.n_rays * self.n_radii


@dataclass(frozen=True)
class SampledField:
    """Poles, the field on them and the indices used to filter the sections."""

    config: SamplingConfig
    force_point: np.ndarray  # P, (3,)
    force: np.ndarray  # F, (3,)
    basis: LineBasis
    plane_offsets: np.ndarray  # s of each plane, (n_planes,)
    poles: np.ndarray  # O, (N, 3)
    moments: np.ndarray  # M(O), (N, 3)
    feet: np.ndarray  # Q, (N, 3)
    axial_offset: np.ndarray  # s, (N,)
    radial_distance: np.ndarray  # |d|, (N,)
    plane_index: np.ndarray  # (N,) int
    ray_index: np.ndarray  # (N,) int
    radius_index: np.ndarray  # (N,) int


def sample_field(
    config: SamplingConfig,
    force_point: np.ndarray,
    force: np.ndarray,
    prev_v1: np.ndarray | None = None,
) -> SampledField:
    """Poles O = P + s·u + r·(cos θ·v1 + sin θ·v2) and M, Q, s, |d| on them, vectorized.

    Planes are equally spaced and centred on P; radii start at one step, so no pole lies on
    the axis, where d = 0 and the radial direction is undefined.
    """
    force_point = np.asarray(force_point, dtype=float)
    force = np.asarray(force, dtype=float)
    basis = line_basis(force, prev_v1=prev_v1)

    plane_offsets = (np.arange(config.n_planes) - (config.n_planes - 1) / 2.0) * config.plane_spacing
    angles = np.deg2rad(np.arange(config.n_rays) * config.angle_step_deg)
    radii = np.arange(1, config.n_radii + 1) * config.radius_step

    plane_idx, ray_idx, radius_idx = (
        grid.ravel()
        for grid in np.meshgrid(
            np.arange(config.n_planes), np.arange(config.n_rays), np.arange(config.n_radii), indexing="ij"
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
    decomposition = axial_decomposition(poles, force_point, force)
    return SampledField(
        config=config,
        force_point=force_point,
        force=force,
        basis=basis,
        plane_offsets=plane_offsets,
        poles=poles,
        moments=moment_field(poles, force_point, force),
        feet=decomposition.foot,
        axial_offset=decomposition.axial_offset,
        radial_distance=decomposition.radial_distance,
        plane_index=plane_idx,
        ray_index=ray_idx,
        radius_index=radius_idx,
    )


# Sections are data filters over the sampled poles, never camera angles.


def normal_section(field: SampledField, plane: int | None = None) -> np.ndarray:
    """Mask of the poles of one plane normal to the axis (the middle one by default)."""
    plane = field.config.n_planes // 2 if plane is None else plane
    return field.plane_index == plane


def axial_section(field: SampledField) -> np.ndarray:
    """Mask of the poles in the plane that contains the axis: rays at 0° and, if sampled, 180°."""
    mask = field.ray_index == 0
    if field.config.n_rays % 2 == 0:
        mask = mask | (field.ray_index == field.config.n_rays // 2)
    return mask
