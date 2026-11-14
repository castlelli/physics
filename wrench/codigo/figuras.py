"""Figures 1 and 2 of the statement (items h and i), matplotlib 3D with equal aspect.

Forces have one arrowhead, moments two (the engineering convention for a moment vector).
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
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from . import estilo  # noqa: E402
from .modelo import Reduction, System  # noqa: E402


@dataclass(frozen=True)
class DrawScale:
    """Presentation only: factors applied before drawing. Forces and R share one, moments another."""

    force: float
    moment: float


def auto_scale(system: System, reduction: Reduction) -> DrawScale:
    """Largest drawn force and largest drawn moment both at 40 % of the box diagonal."""
    diagonal = float(np.linalg.norm([system.box.a, system.box.b, system.box.c]))
    forces = max(float(np.linalg.norm(system.forces, axis=1).max()), float(np.linalg.norm(reduction.resultant)))
    moments = [reduction.moment_q, reduction.moment_a]
    if reduction.minimum_moment is not None:
        moments.append(reduction.minimum_moment)
    biggest = max(float(np.linalg.norm(m)) for m in moments)
    return DrawScale(force=0.4 * diagonal / forces if forces > 0 else 1.0,
                     moment=0.4 * diagonal / biggest if biggest > 0 else 1.0)


def _num(x: float) -> str:
    return f"{x:.3g}".replace(".", ",").replace("-", "−")


# ------------------------------------------------------------------ drawing helpers


class Canvas:
    """One 3D axes plus the points that set its cubic limits."""

    def __init__(self, ax) -> None:
        self.ax = ax
        self.extent: list[np.ndarray] = []

    def arrow(self, start, vector, color, lw=1.4, double=False, label=None) -> None:
        start = np.asarray(start, dtype=float)
        vector = np.asarray(vector, dtype=float)
        if np.linalg.norm(vector) == 0:
            return
        self.ax.quiver(*start, *vector, color=color, lw=lw, arrow_length_ratio=0.16)
        if double:
            # a second head just behind the first one
            self.ax.quiver(*start, *(0.8 * vector), color=color, lw=lw, arrow_length_ratio=0.2)
        self.extent += [start, start + vector]
        if label:
            tip = start + vector * 1.08
            self.ax.text(*tip, label, color=color, fontsize=8.5, ha="center", va="center")

    def point(self, p, label, color="black", offset=(0.06, 0.06, 0.06)) -> None:
        p = np.asarray(p, dtype=float)
        self.ax.scatter(*p, color=color, s=10, depthshade=False)
        self.ax.text(*(p + np.array(offset)), label, color=color, fontsize=8.5)
        self.extent.append(p)

    def line(self, a, b, color, ls="-", lw=1.0) -> None:
        self.ax.plot(*np.array([a, b]).T, color=color, ls=ls, lw=lw)

    def finish(self, view: tuple[float, float]) -> None:
        points = np.array(self.extent)
        centre = 0.5 * (points.min(axis=0) + points.max(axis=0))
        half = max(0.55 * float((points.max(axis=0) - points.min(axis=0)).max()), 0.5)
        for setter, c in zip((self.ax.set_xlim, self.ax.set_ylim, self.ax.set_zlim), centre):
            setter(c - half, c + half)
        self.ax.set_box_aspect((1, 1, 1))  # equal aspect, or right angles render skewed
        self.ax.view_init(*view)
        self.ax.set_xlabel("$x$", labelpad=-8)
        self.ax.set_ylabel("$y$", labelpad=-8)
        self.ax.set_zlabel("$z$", labelpad=-8)
        self.ax.tick_params(labelsize=6, pad=-2)
        estilo.decimal_comma(self.ax, "xyz")
        for axis in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            axis.pane.set_facecolor((1, 1, 1, 0))
            axis.pane.set_edgecolor(estilo.LIGHT_GREY)
            axis._axinfo["grid"]["color"] = estilo.LIGHT_GREY
            axis._axinfo["grid"]["linewidth"] = 0.4


def _box(canvas: Canvas, system: System) -> None:
    a, b, c = system.box.a, system.box.b, system.box.c
    v = np.array([[x, y, z] for x in (0, a) for y in (0, b) for z in (0, c)])
    faces = [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]]
    canvas.ax.add_collection3d(Poly3DCollection([v[f] for f in faces], facecolor=estilo.BOX, alpha=0.07, edgecolor="none"))
    for i in range(8):
        for j in range(i + 1, 8):
            if np.count_nonzero(v[i] != v[j]) == 1:
                canvas.line(v[i], v[j], estilo.BOX, lw=0.8)
    canvas.extent += list(v)


def _frame(canvas: Canvas, system: System) -> None:
    """Oxyz: the reference frame, at the box's corner."""
    length = 0.45 * min(system.box.a, system.box.b, system.box.c) + 0.3
    for e, name in zip(np.eye(3), "xyz"):
        canvas.ax.quiver(0, 0, 0, *(e * length), color=estilo.GREY, lw=0.9, arrow_length_ratio=0.2)
        canvas.ax.text(*(e * length * 1.18), name, color=estilo.GREY, fontsize=8)
    canvas.ax.text(-0.08, -0.08, -0.08, "O", color=estilo.GREY, fontsize=8)


def _forces(canvas: Canvas, system: System, scale: DrawScale) -> None:
    for i, (force, point) in enumerate(zip(system.forces, system.points), start=1):
        canvas.point(point, f"$P_{{{i}}}$", offset=(-0.12, -0.12, -0.1))
        canvas.arrow(point, scale.force * force, estilo.FORCE, lw=1.5, label=f"$F_{{{i}}}$")


def _new(title: str):
    estilo.apply_style()
    fig = plt.figure(figsize=(estilo.WIDTH * 0.8, 5.0))
    ax = fig.add_subplot(projection="3d")
    ax.set_title(title, fontsize=9.5, pad=2)
    return fig, Canvas(ax)


# ------------------------------------------------------------------ figures


def figure_1(system: System, reduction: Reduction, scale: DrawScale, view: tuple[float, float], path: Path) -> Path:
    """Item h: Oxyz, F_i at P_i, Q, the axis Au, R, M_Q and M_A (the last three when non-zero)."""
    fig, canvas = _new("Sistema de forças, polos Q e A e eixo Au")
    _box(canvas, system)
    _frame(canvas, system)
    _forces(canvas, system, scale)
    diagonal = float(np.linalg.norm([system.box.a, system.box.b, system.box.c]))
    A, Q, u = system.pole_a, system.pole_q, reduction.unit_u
    canvas.line(A - 0.6 * diagonal * u, A + 0.6 * diagonal * u, estilo.AXIS_U, ls="-.", lw=1.0)
    canvas.ax.text(*(A + 0.45 * diagonal * u), "  eixo $Au$", color=estilo.AXIS_U, fontsize=8)
    canvas.point(Q, "$Q$", color=estilo.MOMENT_Q)
    canvas.point(A, "$A$", color=estilo.MOMENT_A)
    canvas.arrow(Q, scale.force * reduction.resultant, estilo.RESULTANT, lw=2.0, label="$R$")
    canvas.arrow(Q, scale.moment * reduction.moment_q, estilo.MOMENT_Q, lw=1.6, double=True, label="$M_Q$")
    canvas.arrow(A, scale.moment * reduction.moment_a, estilo.MOMENT_A, lw=1.6, double=True, label="$M_A$")
    canvas.finish(view)
    # the legend names only what is drawn: R, M_Q and M_A appear when they are not zero
    drawn = {"R": reduction.resultant, "MQ": reduction.moment_q, "MA": reduction.moment_a}
    keys = ["F"] + [k for k, v in drawn.items() if np.linalg.norm(v) > 0] + ["Au"]
    fig.legend(handles=_legend(scale, keys), loc="lower center", ncol=3, fontsize=7.5)
    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0.12)
    return _save(fig, path)


def figure_2(system: System, reduction: Reduction, scale: DrawScale, view: tuple[float, float], path: Path) -> Path | None:
    """Item i: Oxyz, F_i at P_i, Q, M_Q and the central axis with R and M_E on it. None without a central axis."""
    if not reduction.has_central_axis:
        return None
    fig, canvas = _new("Eixo central, resultante R e momento mínimo $M_E$")
    _box(canvas, system)
    _frame(canvas, system)
    _forces(canvas, system, scale)
    diagonal = float(np.linalg.norm([system.box.a, system.box.b, system.box.c]))
    E, d = reduction.axis_point, reduction.axis_direction
    # R and M_E go on the axis at the point nearest the box's centre, so they sit on the body when the axis crosses it
    anchor = axis_anchor(system, reduction)
    canvas.line(anchor - 0.8 * diagonal * d, anchor + 0.8 * diagonal * d, estilo.CENTRAL, lw=1.3)
    canvas.point(E, "$E$", color=estilo.CENTRAL, offset=(0.08, -0.12, 0.0))
    canvas.point(system.pole_q, "$Q$", color=estilo.MOMENT_Q)
    canvas.arrow(system.pole_q, scale.moment * reduction.moment_q, estilo.MOMENT_Q, lw=1.6, double=True, label="$M_Q$")
    canvas.arrow(anchor, scale.force * reduction.resultant, estilo.RESULTANT, lw=2.0, label="$R$")
    canvas.arrow(anchor, scale.moment * reduction.minimum_moment, estilo.CENTRAL, lw=1.6, double=True, label="$M_E$")
    canvas.finish(view)
    keys = ("F", "R", "MQ", "E", "ME") if np.linalg.norm(reduction.minimum_moment) > 0 else ("F", "R", "MQ", "E")
    fig.legend(handles=_legend(scale, keys), loc="lower center", ncol=3, fontsize=7.5)
    fig.subplots_adjust(left=0, right=1, top=0.95, bottom=0.12)
    return _save(fig, path)


def axis_anchor(system: System, reduction: Reduction) -> np.ndarray:
    """Point of the central axis nearest the centre of the box."""
    centre = 0.5 * np.array([system.box.a, system.box.b, system.box.c])
    E, d = reduction.axis_point, reduction.axis_direction
    return E + ((centre - E) @ d) * d


def _legend(scale: DrawScale, keys) -> list[Line2D]:
    entries = {
        "F": Line2D([], [], color=estilo.FORCE, lw=1.5, label=f"$F_i$ (×{_num(scale.force)})"),
        "R": Line2D([], [], color=estilo.RESULTANT, lw=2.0, label=f"$R$ (×{_num(scale.force)})"),
        "MQ": Line2D([], [], color=estilo.MOMENT_Q, lw=1.6, label=f"$M_Q$ (×{_num(scale.moment)})"),
        "MA": Line2D([], [], color=estilo.MOMENT_A, lw=1.6, label=f"$M_A$ (×{_num(scale.moment)})"),
        "Au": Line2D([], [], color=estilo.AXIS_U, ls="-.", lw=1.0, label="eixo $Au$"),
        "E": Line2D([], [], color=estilo.CENTRAL, lw=1.3, label="eixo central"),
        "ME": Line2D([], [], color=estilo.CENTRAL, lw=1.6, label=f"$M_E$ (×{_num(scale.moment)})"),
    }
    return [entries[k] for k in keys]


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path
