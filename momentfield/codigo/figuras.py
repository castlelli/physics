"""Figures for the report, with the colours of the statement.

The two sections are drawn in the section's own plane coordinates (exact 2D, no 3D sorting
artefacts); the perspective and the tilted views use matplotlib 3D with equal aspect.
Sections are data filters (modelo.normal_section, modelo.axial_section), never camera angles.
All text the reader sees is pt-BR.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

from . import estilo  # noqa: E402
from .modelo import SampledField, axial_section, normal_section  # noqa: E402


@dataclass(frozen=True)
class DrawScale:
    """Presentation only: factors applied to M and F before drawing. They never change the field."""

    moment: float
    force: float


def auto_scale(field: SampledField) -> DrawScale:
    """Largest drawn moment at 60 % of the largest radius, drawn force at 80 %."""
    max_radius = float(field.radial_distance.max())
    max_moment = float(np.linalg.norm(field.moments, axis=1).max())
    return DrawScale(
        moment=0.6 * max_radius / max_moment if max_moment > 0 else 1.0,
        force=0.8 * max_radius / float(np.linalg.norm(field.force)),
    )


def legend_handles(scale: DrawScale) -> list[Line2D]:
    return [
        Line2D([], [], color=estilo.FORCE, lw=1.6, label=r"$\vec F$ e linha de ação"),
        Line2D([], [], color=estilo.MOMENT, lw=1.2, label=rf"$\vec M(O)$, desenhado $\times${_num(scale.moment)}"),
        Line2D([], [], color=estilo.POLE_TO_FOOT, ls="--", label=r"$O \to Q$"),
        Line2D([], [], color=estilo.TIP_TO_FOOT, ls="--", label=r"ponta de $\vec M(O) \to Q$"),
    ]


def _num(x: float) -> str:
    """Number for running text: three significant digits, decimal comma, typographic minus."""
    return f"{x:.3g}".replace(".", ",").replace("-", "−")


def _mnum(x: float) -> str:
    """Number for mathtext: {,} keeps the comma from adding space."""
    return f"{x:.3g}".replace(".", "{,}")


# ------------------------------------------------------------------ 3D


def _draw_3d(ax, field: SampledField, scale: DrawScale, mask: np.ndarray) -> None:
    poles, moments, feet = field.poles[mask], field.moments[mask], field.feet[mask]
    tips = poles + scale.moment * moments
    p, u = field.force_point, field.basis.u
    drawn_force = scale.force * field.force

    # symmetric cubic limits: without equal aspect the right angles would render skewed
    points = np.vstack([poles, feet, tips, p, p + drawn_force])
    centre = 0.5 * (points.min(axis=0) + points.max(axis=0))
    half = max(0.55 * float((points.max(axis=0) - points.min(axis=0)).max()), 1e-6)

    line = np.array([p - 2.0 * half * u, p + 2.0 * half * u])
    ax.plot(*line.T, color=estilo.FORCE, lw=0.8)
    ax.quiver(*p, *drawn_force, color=estilo.FORCE, lw=1.6, arrow_length_ratio=0.15)
    ax.add_collection3d(Line3DCollection(np.stack([poles, feet], axis=1), colors=estilo.POLE_TO_FOOT,
                                         linestyles="dashed", linewidths=0.6))
    ax.add_collection3d(Line3DCollection(np.stack([tips, feet], axis=1), colors=estilo.TIP_TO_FOOT,
                                         linestyles="dashed", linewidths=0.6))
    ax.quiver(*poles.T, *(scale.moment * moments).T, color=estilo.MOMENT, lw=0.9, arrow_length_ratio=0.15)
    ax.scatter(*poles.T, color=estilo.MOMENT, s=3, depthshade=False)

    for setter, c in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), centre):
        setter(c - half, c + half)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("$x$", labelpad=-8)
    ax.set_ylabel("$y$", labelpad=-8)
    ax.set_zlabel("$z$", labelpad=-8)
    ax.tick_params(labelsize=6, pad=-2)
    estilo.decimal_comma(ax, "xyz")
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((1, 1, 1, 0))
        axis.pane.set_edgecolor(estilo.LIGHT_GREY)
        axis._axinfo["grid"]["color"] = estilo.LIGHT_GREY
        axis._axinfo["grid"]["linewidth"] = 0.4


def _view_toward(direction: np.ndarray, elev_offset: float = 0.0) -> tuple[float, float]:
    """(elev, azim) that put the camera along ``direction``."""
    d = direction / np.linalg.norm(direction)
    return float(np.degrees(np.arcsin(np.clip(d[2], -1, 1)))) + elev_offset, float(np.degrees(np.arctan2(d[1], d[0])))


def perspective(field: SampledField, scale: DrawScale, path: Path,
                views: tuple[tuple[float, float], ...] = ((22.0, -60.0), (12.0, 150.0))) -> Path:
    """Full field, no filter, from two observer positions."""
    fig = plt.figure(figsize=(estilo.WIDTH, 3.5))
    everything = np.ones(len(field.poles), dtype=bool)
    for i, (elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, len(views), i + 1, projection="3d")
        _draw_3d(ax, field, scale, everything)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(f"elevação {_num(elev)}°, azimute {_num(azim)}°", fontsize=8.5, pad=0)
    fig.legend(handles=legend_handles(scale), loc="lower center", ncol=4, fontsize=7.5)
    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0.1, wspace=0.0)
    return _save(fig, path)


def tilted_axial(field: SampledField, scale: DrawScale, path: Path, elev_offset: float = 20.0) -> Path:
    """Axial section seen slightly off its normal, so the out-of-page moments show."""
    fig = plt.figure(figsize=(estilo.WIDTH * 0.62, 3.4))
    ax = fig.add_subplot(projection="3d")
    _draw_3d(ax, field, scale, axial_section(field))
    ax.set_proj_type("ortho")
    ax.view_init(*_view_toward(field.basis.v2, elev_offset=elev_offset))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return _save(fig, path)


# ------------------------------------------------------------------ 2D sections


def _arrow(ax, start, delta, color, lw=0.9, head=0.09) -> None:
    length = float(np.hypot(*delta))
    if length > 0:
        ax.arrow(*start, *delta, color=color, lw=lw, head_width=head, head_length=1.4 * head,
                 length_includes_head=True, zorder=3)


def _plane_coordinates(field: SampledField, points: np.ndarray, axes: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    relative = points - field.force_point
    return np.column_stack([relative @ axes[0], relative @ axes[1]])


def _symbol(ax, xy, outward: bool, size: float, color: str) -> None:
    """⊙ (vector toward the reader) or ⊗ (away), with radius proportional to the magnitude."""
    circle = plt.Circle(xy, size, fill=False, color=color, lw=0.9, zorder=3)
    ax.add_patch(circle)
    if outward:
        ax.plot(*xy, "o", color=color, ms=1.8, zorder=3)
    else:
        k = size / np.sqrt(2)
        ax.plot([xy[0] - k, xy[0] + k], [xy[1] - k, xy[1] + k], color=color, lw=0.9, zorder=3)
        ax.plot([xy[0] - k, xy[0] + k], [xy[1] + k, xy[1] - k], color=color, lw=0.9, zorder=3)


def _section_frame(ax, limit: float, xlabel: str, ylabel: str) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    estilo.decimal_comma(ax)


def normal_section_figure(field: SampledField, scale: DrawScale, path: Path) -> Path:
    """Left: one plane normal to the axis (pinwheel). Right: every plane overlaid, they coincide."""
    b = field.basis
    axes = (b.v1, b.v2)  # u = v1 ∧ v2 points at the reader
    radius = float(field.radial_distance.max())
    limit = 1.25 * radius + 0.1
    fig, (left, right) = plt.subplots(1, 2, figsize=(estilo.WIDTH, 3.2))

    mask = normal_section(field)
    poles = _plane_coordinates(field, field.poles[mask], axes)
    moments = np.column_stack([field.moments[mask] @ b.v1, field.moments[mask] @ b.v2]) * scale.moment
    for o, m in zip(poles, moments):
        left.plot([o[0], 0], [o[1], 0], ls="--", color=estilo.POLE_TO_FOOT, lw=0.7, zorder=1)
        left.plot([o[0] + m[0], 0], [o[1] + m[1], 0], ls="--", color=estilo.TIP_TO_FOOT, lw=0.7, zorder=1)
        _arrow(left, o, m, estilo.MOMENT, head=0.05 * limit)
    left.plot(*poles.T, "o", color=estilo.MOMENT, ms=2)
    _symbol(left, (0.0, 0.0), True, 0.05 * limit, estilo.FORCE)
    s0 = field.plane_offsets[field.config.n_planes // 2]
    left.set_title(f"plano $s = {_mnum(s0)}$: $\\vec F$ aponta para o leitor")
    _section_frame(left, limit, r"$\vec v_1$", r"$\vec v_2$")

    markers = ["o", "s", "^", "D", "v", "P", "X"]
    for k in range(field.config.n_planes):
        sel = field.plane_index == k
        o = _plane_coordinates(field, field.poles[sel], axes)
        m = np.column_stack([field.moments[sel] @ b.v1, field.moments[sel] @ b.v2]) * scale.moment
        for start, delta in zip(o, m):
            _arrow(right, start, delta, estilo.MOMENT, lw=0.6, head=0.05 * limit)
        right.plot(*o.T, markers[k % len(markers)], mfc="none", color=estilo.GREY, ms=3 + 1.6 * k, mew=0.6,
                   label=f"$s = {_mnum(field.plane_offsets[k])}$")
    _symbol(right, (0.0, 0.0), True, 0.05 * limit, estilo.FORCE)
    right.set_title(f"os {field.config.n_planes} planos sobrepostos")
    right.legend(loc="upper right", fontsize=7, handlelength=1)
    _section_frame(right, limit, r"$\vec v_1$", "")
    fig.tight_layout()
    return _save(fig, path)


def axial_section_figure(field: SampledField, scale: DrawScale, path: Path) -> Path:
    """Left: the plane that contains the axis, M normal to the page. Right: M along the normal vs signed distance."""
    b = field.basis
    out_of_page = np.cross(b.v1, b.u)  # (v1, u) on the page, this normal points at the reader
    mask = axial_section(field)
    coords = _plane_coordinates(field, field.poles[mask], (b.v1, b.u))
    feet = _plane_coordinates(field, field.feet[mask], (b.v1, b.u))
    m_out = field.moments[mask] @ out_of_page
    limit = 1.2 * max(float(np.abs(coords).max()), float(field.radial_distance.max())) + 0.1

    fig, (left, right) = plt.subplots(1, 2, figsize=(estilo.WIDTH, 3.3), gridspec_kw={"width_ratios": [1, 1.1]})
    left.plot([0, 0], [-limit, limit], color=estilo.FORCE, lw=0.8)
    _arrow(left, (0.0, 0.0), (0.0, float(np.linalg.norm(field.force)) * scale.force), estilo.FORCE, lw=1.4,
           head=0.05 * limit)
    biggest = float(np.abs(m_out).max())
    for o, q, m in zip(coords, feet, m_out):
        left.plot([o[0], q[0]], [o[1], q[1]], ls="--", color=estilo.POLE_TO_FOOT, lw=0.7, zorder=1)
        _symbol(left, o, m > 0, 0.09 * limit * abs(m) / biggest, estilo.MOMENT)
    left.set_title(r"$\odot$ sai da página, $\otimes$ entra; raio $\propto |\vec M|$")
    _section_frame(left, limit, r"$\vec v_1$ (distância com sinal)", r"$\vec u$ (ao longo de $\vec F$)")

    signed = coords[:, 0]
    norm_f = float(np.linalg.norm(field.force))
    x = np.linspace(-1.1 * np.abs(signed).max(), 1.1 * np.abs(signed).max(), 2)
    right.axhline(0, color=estilo.LIGHT_GREY, lw=0.6)
    right.axvline(0, color=estilo.LIGHT_GREY, lw=0.6)
    right.plot(x, -norm_f * x, color=estilo.GREY, lw=0.8, label=r"$-|\vec F|\,d$")
    for k in range(field.config.n_planes):
        sel = field.plane_index[mask] == k
        right.plot(signed[sel], m_out[sel], "o", mfc="none", color=estilo.MOMENT, ms=3 + 1.6 * k, mew=0.6)
    right.set_xlabel(r"distância com sinal $d$")
    right.set_ylabel(r"componente de $\vec M$ normal à página")
    right.set_title(f"todos os planos: uma reta de inclinação $-|\\vec F| = -{_mnum(norm_f)}$")
    right.legend(loc="upper right", fontsize=7)
    estilo.decimal_comma(right)
    fig.tight_layout()
    return _save(fig, path)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def generate(field: SampledField, folder: Path) -> dict[str, Path]:
    """Every report figure for one sampled field."""
    estilo.apply_style()
    scale = auto_scale(field)
    return {
        "perspectiva": perspective(field, scale, folder / "perspectiva.pdf"),
        "corte_normal": normal_section_figure(field, scale, folder / "corte_normal.pdf"),
        "corte_axial": axial_section_figure(field, scale, folder / "corte_axial.pdf"),
        "inclinada": tilted_axial(field, scale, folder / "inclinada.pdf"),
    }
