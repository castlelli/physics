"""Static matplotlib figures for the written report.

Assignment colors (fixed by the statement, do not change):
- red: force F and its line of action;
- black: moment vectors M(O);
- green dashed: pole O → foot Q;
- blue dashed: drawn tip of M(O) → foot Q.

Sections are data filters over the sample set, not camera angles.
All user-facing text (titles, legends) is Portuguese (pt-BR).
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from momentfield.sampling import SampledField

COLOR_FORCE = "red"
COLOR_MOMENT = "black"
COLOR_POLE_TO_FOOT = "green"
COLOR_TIP_TO_FOOT = "blue"

# default observer positions for the perspective pages: (elev, azim) in degrees
DEFAULT_PERSPECTIVE_ANGLES: tuple[tuple[float, float], ...] = (
    (22.0, -60.0),
    (35.0, 45.0),
    (10.0, 150.0),
    (65.0, -120.0),
)


@dataclass(frozen=True)
class RenderOptions:
    """Presentation-only knobs; they never change the underlying field."""

    moment_scale: float  # multiplies M(O) before drawing (see legend trade-off note)
    force_scale: float  # multiplies F before drawing (direction/sense only)


def auto_render_options(field: SampledField) -> RenderOptions:
    """Scales chosen so the largest drawn vector stays comparable to the sampling radius."""
    max_radius = float(field.radial_distance.max())
    max_moment = float(np.linalg.norm(field.moments, axis=1).max())
    force_norm = float(np.linalg.norm(field.force))
    moment_scale = 0.6 * max_radius / max_moment if max_moment > 0 else 1.0
    force_scale = 0.8 * max_radius / force_norm if force_norm > 0 else 1.0
    return RenderOptions(moment_scale=moment_scale, force_scale=force_scale)


def _view_toward(direction: np.ndarray, elev_offset: float = 0.0) -> tuple[float, float]:
    """(elev, azim) placing the matplotlib camera along ``direction``, looking at the scene."""
    d = direction / np.linalg.norm(direction)
    elev = float(np.degrees(np.arcsin(np.clip(d[2], -1.0, 1.0))))
    azim = float(np.degrees(np.arctan2(d[1], d[0])))
    return elev + elev_offset, azim


def _draw_field(
    ax,
    field: SampledField,
    options: RenderOptions,
    mask: np.ndarray,
) -> None:
    """Draw the (possibly filtered) field with the assignment colors and equal aspect."""
    poles = field.poles[mask]
    moments = field.moments[mask]
    feet = field.feet[mask]
    tips = poles + options.moment_scale * moments

    p = field.force_point
    u = field.basis.u
    drawn_force = options.force_scale * field.force

    # symmetric cubic limits: without equal aspect the right angles render skewed
    extent_points = np.vstack([poles, feet, tips, p[None, :], (p + drawn_force)[None, :]])
    center = 0.5 * (extent_points.min(axis=0) + extent_points.max(axis=0))
    half = 0.55 * float((extent_points.max(axis=0) - extent_points.min(axis=0)).max())
    half = max(half, 1e-6)

    # line of action across the whole box, then the force applied at P — both red
    line = np.array([p - 2.0 * half * u, p + 2.0 * half * u])
    ax.plot(*line.T, color=COLOR_FORCE, linewidth=1.0)
    ax.quiver(*p, *drawn_force, color=COLOR_FORCE, linewidth=2.0, arrow_length_ratio=0.12)
    ax.scatter(*p, color=COLOR_FORCE, s=25)

    # moment vectors (black) at each pole
    ax.quiver(
        poles[:, 0], poles[:, 1], poles[:, 2],
        options.moment_scale * moments[:, 0],
        options.moment_scale * moments[:, 1],
        options.moment_scale * moments[:, 2],
        color=COLOR_MOMENT, linewidth=1.0, arrow_length_ratio=0.12,
    )
    ax.scatter(*poles.T, color=COLOR_MOMENT, s=6)

    # dashed construction lines: O → Q (green) and drawn tip of M → Q (blue)
    ax.add_collection3d(
        Line3DCollection(np.stack([poles, feet], axis=1), colors=COLOR_POLE_TO_FOOT,
                         linestyles="dashed", linewidths=0.9)
    )
    ax.add_collection3d(
        Line3DCollection(np.stack([tips, feet], axis=1), colors=COLOR_TIP_TO_FOOT,
                         linestyles="dashed", linewidths=0.9)
    )

    for setter, axis_center in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
        setter(axis_center - half, axis_center + half)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")


def _legend(ax, options: RenderOptions) -> None:
    handles = [
        Line2D([], [], color=COLOR_FORCE, linewidth=2.0,
               label="F e linha de ação"),
        Line2D([], [], color=COLOR_MOMENT, linewidth=1.5,
               label=f"M(O), escala ×{options.moment_scale:.3g}"),
        Line2D([], [], color=COLOR_POLE_TO_FOOT, linestyle="--",
               label="O → Q (pé da perpendicular)"),
        Line2D([], [], color=COLOR_TIP_TO_FOOT, linestyle="--",
               label="ponta de M(O) → Q"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)


_SCALE_NOTE = (
    "Vetores M(O) desenhados com fator de escala; as linhas azuis vão até a ponta "
    "desenhada (escalada): a perpendicularidade do triângulo O–Q–ponta é preservada, "
    "mas não seu comprimento métrico."
)


def _new_figure(title: str) -> tuple[Figure, object]:
    fig = Figure(figsize=(9.0, 7.5))
    ax = fig.add_subplot(projection="3d")
    ax.set_title(title, fontsize=11)
    fig.text(0.5, 0.02, _SCALE_NOTE, ha="center", fontsize=7, style="italic", wrap=True)
    return fig, ax


def figure_perspective(
    field: SampledField,
    options: RenderOptions,
    elev: float,
    azim: float,
) -> Figure:
    """Full field, arbitrary observer position — no data filter."""
    fig, ax = _new_figure(
        "Campo de momentos M(O) = (P − O) ∧ F — vista em perspectiva\n"
        f"(elevação {elev:.0f}°, azimute {azim:.0f}°)"
    )
    _draw_field(ax, field, options, mask=np.ones(len(field.poles), dtype=bool))
    _legend(ax, options)
    ax.view_init(elev=elev, azim=azim)
    return fig


def figure_section_normal(field: SampledField, options: RenderOptions) -> Figure:
    """Single plane Π normal to the axis, viewed along the axis: the 60°-invariant pinwheel."""
    middle_plane = field.config.n_planes // 2
    mask = field.plane_index == middle_plane
    fig, ax = _new_figure(
        "Seção normal à linha de ação (um único plano de polos)\n"
        "M(O) tangencial — figura invariante sob rotações de 60° em torno do eixo"
    )
    _draw_field(ax, field, options, mask=mask)
    _legend(ax, options)
    # orthographic projection: right angles must not be skewed by perspective
    ax.set_proj_type("ortho")
    ax.view_init(*_view_toward(field.basis.u))
    return fig


def figure_section_axial(
    field: SampledField, options: RenderOptions, elev_offset: float = 0.0
) -> Figure:
    """Poles in the plane containing the axis (rays at 0° and 180°), viewed along its normal.

    With ``elev_offset = 0`` the view is exactly along the plane normal and the
    moments collapse to points — that IS the demonstration that M ⊥ plane.
    A small offset tilts the camera just enough to show the out-of-page vectors.
    """
    opposite_ray = field.config.n_rays // 2
    mask = (field.ray_index == 0) | (field.ray_index == opposite_ray)
    subtitle = (
        "M(O) normal à página — módulo linear em |d|, sentido trocando através do eixo"
        if elev_offset == 0.0
        else "vista ligeiramente inclinada para evidenciar os vetores M(O) saindo da página"
    )
    fig, ax = _new_figure(
        f"Seção contendo a linha de ação (polos do plano axial)\n{subtitle}"
    )
    _draw_field(ax, field, options, mask=mask)
    _legend(ax, options)
    ax.set_proj_type("ortho")
    ax.view_init(*_view_toward(field.basis.v2, elev_offset=elev_offset))
    return fig


def _title_page(
    field: SampledField,
    options: RenderOptions,
    verification_lines: list[str] | None,
) -> Figure:
    fig = Figure(figsize=(9.0, 7.5))
    p = field.force_point
    f = field.force
    cfg = field.config
    lines = [
        "Campo de momentos de uma força",
        "Mecânica I — Escola Politécnica da USP",
        "Vinicius Castelli",
        "Repositório: https://github.com/castlelli/openfields",
        "",
        "M(O) = (P − O) ∧ F        (momento de F, aplicada em P, em relação ao polo O)",
        "",
        f"Ponto de aplicação:  P = ({p[0]:g}, {p[1]:g}, {p[2]:g})",
        f"Força:               F = ({f[0]:g}, {f[1]:g}, {f[2]:g}),   |F| = {np.linalg.norm(f):g}",
        "",
        "Amostragem dos polos O:",
        f"  {cfg.n_planes} planos normais à linha de ação, espaçados de {cfg.plane_spacing:g};",
        f"  {cfg.n_rays} raios por plano (passo angular de {cfg.angle_step_deg:g}°);",
        f"  {cfg.n_radii} distâncias por raio (passo radial de {cfg.radius_step:g}).",
        "",
        f"Escala de desenho dos momentos: ×{options.moment_scale:.3g}",
        "",
        "Cores:  F e linha de ação em vermelho;  M(O) em preto;",
        "        O → Q em verde tracejado;  ponta de M(O) → Q em azul tracejado.",
        "",
        *textwrap.wrap(_SCALE_NOTE, width=88),
    ]
    if verification_lines:
        lines += ["", "Verificação numérica da axissimetria:"] + [
            f"  {line}" for line in verification_lines
        ]
    fig.text(0.08, 0.92, "\n".join(lines), va="top", fontsize=10, family="DejaVu Sans")
    return fig


def make_report_pdf(
    field: SampledField,
    path: str,
    options: RenderOptions | None = None,
    perspective_angles: tuple[tuple[float, float], ...] = DEFAULT_PERSPECTIVE_ANGLES,
    verification_lines: list[str] | None = None,
) -> None:
    """Write the full report PDF: title page, perspectives, and the two sections."""
    if options is None:
        options = auto_render_options(field)
    with PdfPages(path) as pdf:
        pdf.savefig(_title_page(field, options, verification_lines))
        for elev, azim in perspective_angles:
            pdf.savefig(figure_perspective(field, options, elev, azim))
        pdf.savefig(figure_section_normal(field, options))
        pdf.savefig(figure_section_axial(field, options))
        pdf.savefig(figure_section_axial(field, options, elev_offset=18.0))
        info = pdf.infodict()
        info["Title"] = "Campo de momentos de uma força — Mecânica I"
        info["Subject"] = "M(O) = (P − O) ∧ F: axissimetria em torno da linha de ação"
