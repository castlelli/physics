"""PDF report: sampled field → figures and formatted numbers → LaTeX template (jinja2) → tectonic.

Every number in the text comes from this module. ``check_claims`` stops the build if a result
no longer supports a sentence written in the template.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import figuras
from .casos import CASES
from .modelo import SampledField, axial_section, rotation_about_axis, sample_field
from .verificacao import RELATIVE_TOLERANCE, ProofReport, run_proofs

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
LIVE_SITE = "https://castlelli.github.io/physics/momentfield/"


def num(x: float, digits: int = 3) -> str:
    """Number for math mode: significant digits, decimal comma."""
    x = float(x)
    if x == 0:
        return "0"
    text = f"{x:.{digits}g}"
    if "e" in text:
        return sci(x, digits)
    return text.replace(".", "{,}")


def sci(x: float, digits: int = 2) -> str:
    """Scientific notation for math mode, e.g. 1{,}2\\cdot10^{-16}."""
    x = float(x)
    if x == 0:
        return "0"
    exponent = math.floor(math.log10(abs(x)))
    mantissa = f"{x / 10**exponent:.{digits - 1}f}".replace(".", "{,}")
    return f"{mantissa}\\cdot10^{{{exponent}}}"


def vector(v) -> str:
    return "(" + ";\\ ".join(num(c, 4) for c in v) + ")"


# ------------------------------------------------------------------ claims


def plane_spread(field: SampledField) -> float:
    """Largest difference between the moment at a pole and at its copy on another plane, relative to max |M|."""
    cfg = field.config
    stacked = field.moments.reshape(cfg.n_planes, cfg.n_rays * cfg.n_radii, 3)
    spread = np.abs(stacked - stacked[cfg.n_planes // 2]).max()
    return float(spread / np.linalg.norm(field.moments, axis=1).max())


def rotation_spread(field: SampledField) -> float:
    """Rotate one plane's poles and moments by the angle step: they land on the poles and moments of the same plane."""
    cfg = field.config
    rotation = rotation_about_axis(field.basis.u, math.radians(cfg.angle_step_deg))
    plane = field.plane_index == cfg.n_planes // 2
    poles = field.poles[plane] - field.force_point
    moments = field.moments[plane]
    rotated_poles = poles @ rotation.T
    rotated_moments = moments @ rotation.T
    # pair every rotated pole with the nearest original one
    nearest = np.argmin(np.linalg.norm(rotated_poles[:, None, :] - poles[None, :, :], axis=2), axis=1)
    pole_error = np.abs(rotated_poles - poles[nearest]).max()
    moment_error = np.abs(rotated_moments - moments[nearest]).max()
    return float(max(pole_error / np.abs(poles).max(), moment_error / np.linalg.norm(moments, axis=1).max()))


def axial_line_error(field: SampledField) -> float:
    """In the plane that contains the axis, |M_n + |F|·d| relative to max |M| (M_n: component normal to the page)."""
    b = field.basis
    mask = axial_section(field)
    signed = (field.poles[mask] - field.force_point) @ b.v1
    normal = field.moments[mask] @ np.cross(b.v1, b.u)
    in_page = field.moments[mask] - normal[:, None] * np.cross(b.v1, b.u)
    scale = np.linalg.norm(field.moments, axis=1).max()
    return float(max(np.abs(normal + np.linalg.norm(field.force) * signed).max(), np.abs(in_page).max()) / scale)


def check_claims(field: SampledField, proofs: dict[str, ProofReport]) -> dict[str, float]:
    claims = {
        "plane_spread": plane_spread(field),
        "rotation_spread": rotation_spread(field),
        "axial_line": axial_line_error(field),
    }
    for name, value in claims.items():
        assert value < RELATIVE_TOLERANCE, f"a afirmação '{name}' do texto não vale mais: {value:.3g}"
    for key, report in proofs.items():
        assert report.passed, f"a verificação do caso {key} falhou: {report.relative()}"
        # the text says every error is of the order of 1e-16 (double-precision rounding)
        assert max(report.relative().values()) < 1e-14, f"erros do caso {key} acima de 1e-14"
    assert field.config.angle_step_deg == 60.0 and field.config.n_rays == 6, "o texto fala em 6 raios a 60°"
    return claims


# ------------------------------------------------------------------ numbers for the template


def template_numbers(field: SampledField, scale: figuras.DrawScale, proofs: dict[str, ProofReport],
                     claims: dict[str, float]) -> dict:
    cfg = field.config
    return {
        "P": vector(field.force_point),
        "F": vector(field.force),
        "normF": num(np.linalg.norm(field.force), 4),
        "u": vector(field.basis.u),
        "v1": vector(field.basis.v1),
        "v2": vector(field.basis.v2),
        "n_planes": cfg.n_planes,
        "spacing": num(cfg.plane_spacing),
        "n_rays": cfg.n_rays,
        "step": num(cfg.angle_step_deg),
        "n_radii": cfg.n_radii,
        "radius_step": num(cfg.radius_step),
        "n_samples": cfg.n_samples,
        "max_M": num(np.linalg.norm(field.moments, axis=1).max(), 4),
        "moment_scale": num(scale.moment),
        "tolerance": sci(RELATIVE_TOLERANCE, 1),
        "plane_spread": sci(claims["plane_spread"]) if claims["plane_spread"] else "0",
        "rotation_spread": sci(claims["rotation_spread"]) if claims["rotation_spread"] else "0",
        "axial_line": sci(claims["axial_line"]) if claims["axial_line"] else "0",
        "proofs": [
            {
                "title": CASES[key].title,
                "P": vector(CASES[key].force_point),
                "F": vector(CASES[key].force),
                "n": report.n_poles,
                **{name: sci(value) if value else "0" for name, value in report.relative().items()},
            }
            for key, report in proofs.items()
        ],
    }


# ------------------------------------------------------------------ build

_WARNING = re.compile(r"(LaTeX Warning|Package \S+ Warning|Overfull \\hbox \((\d+\.?\d*)pt|Overfull \\vbox|Missing character)")
# Times New Roman has no OpenType math features; fontspec's warning about it is expected.
_EXPECTED = re.compile(r"fontspec Warning: (Font \"times|OpenType feature 'Style=MathScript)")


def tool(name: str) -> str:
    path = shutil.which(name) or shutil.which(name, path=str(Path(sys.prefix) / "bin"))
    if path is None:
        raise RuntimeError(f"'{name}' não encontrado. Instale-o (ex.: micromamba install {name}).")
    return path


def compile_tex(tex: Path) -> list[str]:
    proc = subprocess.run([tool("tectonic"), "--keep-logs", "--chatter", "minimal", tex.name],
                          cwd=tex.parent, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao compilar {tex.name}:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
    warnings = [line.strip() for line in proc.stderr.splitlines() if line.lower().startswith("warning")]
    for line in tex.with_suffix(".log").read_text(errors="replace").splitlines():
        match = _WARNING.search(line)
        if match and not (match.group(2) and float(match.group(2)) <= 1.0) and not _EXPECTED.search(line):
            warnings.append(line.strip())
    return warnings


def build_report(target: Path) -> Path:
    case = CASES["relatorio"]
    field = sample_field(case.config, case.force_point, case.force)
    proofs = {key: run_proofs(c.force_point, c.force) for key, c in CASES.items()}
    claims = check_claims(field, proofs)
    scale = figuras.auto_scale(field)
    figuras.generate(field, BUILD / "figs")

    env = Environment(loader=FileSystemLoader(ROOT / "codigo" / "templates"), undefined=StrictUndefined,
                      block_start_string=r"\BLOCK{", block_end_string="}", variable_start_string=r"\VAR{",
                      variable_end_string="}", comment_start_string=r"\#{", comment_end_string="}",
                      line_comment_prefix="%#", trim_blocks=True, autoescape=False)
    body = env.get_template("relatorio.tex.j2").render(r=template_numbers(field, scale, proofs, claims), site=LIVE_SITE)

    BUILD.mkdir(exist_ok=True)
    for resource in (ROOT / "codigo" / "recursos").iterdir():  # cover crests
        shutil.copy(resource, BUILD / resource.name)
    fonts = list((Path(sys.prefix) / "fonts").glob("times*.ttf"))  # Microsoft licence: kept out of the repository
    if len(fonts) < 4:
        raise RuntimeError("Times New Roman não encontrada. Instale-a: micromamba install -c conda-forge mscorefonts")
    for font in fonts:
        shutil.copy(font, BUILD / font.name)
    tex = BUILD / "relatorio_momentos.tex"
    tex.write_text(body, encoding="utf-8")
    warnings = compile_tex(tex)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tex.with_suffix(".pdf"), target)
    print(f"PDF: {target}")
    for warning in warnings:
        print("aviso:", warning)
    return target
