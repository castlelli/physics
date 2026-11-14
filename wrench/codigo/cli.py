"""Command line. Reads the statement's inputs (or a ready-made case or a JSON file), prints the
results table and draws figures 1 and 2. User-facing text is pt-BR."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from .casos import BOX, CASES
from .modelo import COUPLE, FORCE_COUPLE, NULL, SINGLE_FORCE, Box, InputError, Reduction, System, reduce

ROOT = Path(__file__).resolve().parent.parent

CATEGORY = {
    NULL: "nulo",
    COUPLE: "redutível a um binário",
    SINGLE_FORCE: "redutível a uma única força",
    FORCE_COUPLE: "redutível a força + binário",
}
SHAPE = {"parallel": "paralelas", "concurrent": "concorrentes", "coplanar": "coplanares"}


def num(x: float) -> str:
    x = 0.0 if abs(x) < 5e-13 else float(x)  # no "−0,0000" for rounding noise
    return f"{x:.4f}".replace(".", ",").replace("-", "−")


def vec(v) -> str:
    return "(" + "; ".join(num(c) for c in v) + ")"


def table_rows(reduction: Reduction) -> list[tuple[str, str, str]]:
    """(quantity, value, magnitude or note) for every output item of the statement."""
    r = reduction
    rows = [
        ("a) resultante R", vec(r.resultant), num(np.linalg.norm(r.resultant))),
        ("b) momento M_Q", vec(r.moment_q), num(np.linalg.norm(r.moment_q))),
        ("c) momento M_A", vec(r.moment_a), num(np.linalg.norm(r.moment_a))),
        ("d) torque no eixo Au", num(r.axis_torque), f"vetor {vec(r.axis_torque_vector)}"),
        ("e) invariante I = R·M", num(r.invariant), ""),
        ("f) sistema", CATEGORY[r.category], ", ".join(SHAPE[s] for s in r.shape) and f"forças {', '.join(SHAPE[s] for s in r.shape)}"),
    ]
    if r.has_central_axis:
        rows += [
            ("g) eixo central: ponto E", vec(r.axis_point), "ponto do eixo mais próximo de Q"),
            ("g) eixo central: direção", vec(r.axis_direction), "versor de R"),
            ("g) momento mínimo M_E", vec(r.minimum_moment), num(np.linalg.norm(r.minimum_moment))),
        ]
    else:
        rows.append(("g) eixo central", "não existe", "R = 0"))
    return rows


def print_table(system: System, reduction: Reduction) -> None:
    print(f"n = {system.n} {'força' if system.n == 1 else 'forças'}")
    for i, (f, p) in enumerate(zip(system.forces, system.points), start=1):
        outside = "" if system.box.contains(p) else "   (fora da caixa)"
        print(f"  F{i} = {vec(f)} em P{i} = {vec(p)}{outside}")
    print(f"  Q = {vec(system.pole_q)}   A = {vec(system.pole_a)}   u = {vec(reduction.unit_u)}")
    rows = table_rows(reduction)
    w0 = max(len(r[0]) for r in rows)
    w1 = max(len(r[1]) for r in rows)
    print("-" * (w0 + w1 + 30))
    for name, value, note in rows:
        print(f"{name:<{w0}}  {value:<{w1}}  {note}")
    print("-" * (w0 + w1 + 30))


def write_csv(reduction: Reduction, path: Path) -> Path:
    r = reduction
    rows = [("R", *r.resultant), ("M_Q", *r.moment_q), ("M_A", *r.moment_a), ("torque_Au", *r.axis_torque_vector)]
    if r.has_central_axis:
        rows += [("E", *r.axis_point), ("direcao_eixo", *r.axis_direction), ("M_E", *r.minimum_moment)]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["grandeza", "x", "y", "z", "modulo"])
        for name, x, y, z in rows:
            writer.writerow([name, f"{x:.12g}", f"{y:.12g}", f"{z:.12g}", f"{np.linalg.norm([x, y, z]):.12g}"])
        writer.writerow(["invariante_I", f"{r.invariant:.12g}", "", "", ""])
        writer.writerow(["torque_Au_escalar", f"{r.axis_torque:.12g}", "", "", ""])
        writer.writerow(["categoria", r.category, "", "", ""])
    return path


def run(system: System, target: Path, view: tuple[float, float] = (24.0, -58.0)) -> list[Path]:
    from . import figuras

    reduction = reduce(system)
    print_table(system, reduction)
    target.mkdir(parents=True, exist_ok=True)
    scale = figuras.auto_scale(system, reduction)
    files = [figuras.figure_1(system, reduction, scale, view, target / "figura1.pdf")]
    second = figuras.figure_2(system, reduction, scale, view, target / "figura2.pdf")
    if second:
        files.append(second)
    else:
        print("sem eixo central: a figura 2 não se aplica")
    files.append(write_csv(reduction, target / "tabela.csv"))
    print("arquivos: " + ", ".join(str(f.relative_to(ROOT) if f.is_relative_to(ROOT) else f) for f in files))
    return files


def ask_vector(label: str) -> np.ndarray:
    while True:
        text = input(f"{label} (3 números): ").replace(",", " ").split()
        try:
            if len(text) == 3:
                return np.array([float(t) for t in text])
        except ValueError:
            pass
        print("  Digite 3 números separados por espaço.")


def ask_system() -> System:
    while True:
        try:
            n = int(input("Número n de forças (n ≥ 1): "))
            if n >= 1:
                break
        except ValueError:
            pass
        print("  n deve ser um inteiro maior ou igual a 1.")
    forces, points = [], []
    for i in range(1, n + 1):
        forces.append(ask_vector(f"F{i} = (Fx, Fy, Fz)"))
        points.append(ask_vector(f"P{i} = (x, y, z)"))
    return System(np.array(forces), np.array(points), ask_vector("Polo Q"), ask_vector("Polo A"), ask_vector("Versor u"), BOX)


def system_from_json(path: Path) -> System:
    data = json.loads(path.read_text(encoding="utf-8"))
    box = Box(*data["box"]) if "box" in data else BOX
    return System(np.array(data["forces"]), np.array(data["points"]), np.array(data["Q"]), np.array(data["A"]), np.array(data["u"]), box)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m codigo",
        description="Redução de um sistema de forças: resultante, momentos em Q e A, torque no eixo Au, "
                    "invariante, classificação, eixo central e momento mínimo.",
    )
    ap.add_argument("--caso", choices=sorted(CASES), help="sistema pronto")
    ap.add_argument("--arquivo", type=Path, help='JSON com "forces", "points", "Q", "A", "u" e, opcional, "box": [a, b, c]')
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: resultado/<caso> ou resultado/execucao)")
    ap.add_argument("--site", action="store_true", help="exporta os dados do site interativo (docs/wrench/data)")
    ap.add_argument("--todos", action="store_true", help="todos os casos prontos e os dados do site")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.site or args.todos:
            from .site import export_site

            print(f"dados do site gravados em {export_site() / 'data'}")
        if args.todos:
            for key, case in CASES.items():
                print(f"\n=== {case.title}")
                run(case.system(), ROOT / "resultado" / key, case.view)
        if args.site or args.todos:
            return 0
        if args.caso:
            case = CASES[args.caso]
            run(case.system(), args.saida or ROOT / "resultado" / args.caso, case.view)
            return 0
        system = system_from_json(args.arquivo) if args.arquivo else ask_system()
        run(system, args.saida or ROOT / "resultado" / "execucao")
        return 0
    except InputError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
