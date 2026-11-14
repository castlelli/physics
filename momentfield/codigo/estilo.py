"""Figure style: the PDF's typography (Times New Roman) and the colours fixed by the statement."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

# Colours required by the assignment statement; do not change.
FORCE = "#D62728"  # red: F and its line of action
MOMENT = "black"  # M(O)
POLE_TO_FOOT = "#2CA02C"  # green dashed: O → Q
TIP_TO_FOOT = "#1F5FD6"  # blue dashed: drawn tip of M(O) → Q
GREY = "#6B7280"
LIGHT_GREY = "#D7DBE0"
WIDTH = 6.3  # inches = 16 cm, the text width of the PDF


def register_times() -> None:
    """Make the environment's Times New Roman (mscorefonts package) available to matplotlib."""
    for font in (Path(sys.prefix) / "fonts").glob("times*.ttf"):
        font_manager.fontManager.addfont(font)


def apply_style() -> None:
    register_times()
    mpl.rcParams.update({
        "font.family": ["Times New Roman", "STIXGeneral"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        "mathtext.bf": "Times New Roman:bold",
        "mathtext.cal": "Times New Roman:italic",
        "mathtext.sf": "Times New Roman",
        "mathtext.tt": "DejaVu Sans Mono",
        "mathtext.fallback": "stix",
        "font.size": 9,
        "axes.titlesize": 9.5,
        "axes.labelsize": 9,
        "axes.linewidth": 0.7,
        "axes.grid": False,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "lines.linewidth": 0.9,
        "axes.unicode_minus": True,
        "pdf.fonttype": 42,
        "savefig.dpi": 400,
    })


def _comma(x: float, _pos=None) -> str:
    return f"{x:.10g}".replace(".", ",").replace("-", "−")


def decimal_comma(ax, axes: str = "xy") -> None:
    """Tick labels with a decimal comma and a typographic minus."""
    formatter = FuncFormatter(_comma)
    if "x" in axes:
        ax.xaxis.set_major_formatter(formatter)
    if "y" in axes:
        ax.yaxis.set_major_formatter(formatter)
    if "z" in axes:
        ax.zaxis.set_major_formatter(formatter)
