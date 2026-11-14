"""Command line. Reads P and F (or a ready-made case), checks the axisymmetry and draws the figures.

User-facing text is pt-BR.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .casos import CASES
from .modelo import InputError, SamplingConfig, sample_field
from .verificacao import run_proofs

ROOT = Path(__file__).resolve().parent.parent

PROOF_LABELS = {
    "axial_component": "máx |M·u| (M normal ao eixo)",
    "magnitude": "máx ||M| − |F|·|d|| (módulo linear na distância)",
    "translation": "máx |M(O + t·u) − M(O)| (translação ao longo do eixo)",
    "rotation": "máx |M(R·O) − R·M(O)| (rotação em torno do eixo)",
}


def ask_vector(label: str, example: str) -> np.ndarray:
    while True:
        text = input(f"{label} (ex.: {example}): ").replace(",", " ").split()
        try:
            if len(text) == 3:
                return np.array([float(t) for t in text])
        except ValueError:
            pass
        print("  Digite 3 números separados por espaço.")


def run(force_point, force, config: SamplingConfig, target: Path) -> list[Path]:
    """Sample the field, print the proofs, write the figures and the samples (JSON contract)."""
    from . import figuras
    from .site import field_to_contract

    field = sample_field(config, force_point, force)
    report = run_proofs(force_point, force)
    vec = lambda v: "(" + ", ".join(f"{c:.6g}" for c in v) + ")"  # noqa: E731
    print(f"P = {vec(field.force_point)}   F = {vec(field.force)}   |F| = {np.linalg.norm(field.force):.6g}")
    print(f"{config.n_planes} planos × {config.n_rays} raios × {config.n_radii} distâncias = {config.n_samples} polos")
    print(f"verificação em {report.n_poles} polos sorteados, erros relativos ao maior |M|:")
    for key, value in report.relative().items():
        print(f"  {PROOF_LABELS[key]}: {value:.2e}")
    print("  axissimetria confirmada" if report.passed else "  ATENÇÃO: alguma verificação passou da tolerância")

    target.mkdir(parents=True, exist_ok=True)
    files = list(figuras.generate(field, target).values())
    samples = target / "amostras.json"
    samples.write_text(json.dumps(field_to_contract(field), indent=1), encoding="utf-8")
    files.append(samples)
    print("arquivos: " + ", ".join(str(f.relative_to(ROOT) if f.is_relative_to(ROOT) else f) for f in files))
    return files


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m codigo",
        description="Campo de momentos de uma força, M(O) = (P − O) ∧ F: figuras e prova da axissimetria.",
    )
    ap.add_argument("--P", nargs=3, type=float, metavar=("Px", "Py", "Pz"), help="ponto de aplicação da força")
    ap.add_argument("--F", nargs=3, type=float, metavar=("Fx", "Fy", "Fz"), help="força")
    ap.add_argument("--caso", choices=sorted(CASES), help="dados prontos (relatorio ou campo1, o exemplo do professor)")
    ap.add_argument("--planos", type=int, help="número de planos normais à linha de ação (padrão: 3)")
    ap.add_argument("--espacamento", type=float, help="distância entre planos (padrão: 1,5)")
    ap.add_argument("--passo-angular", type=float, help="ângulo entre raios, em graus; deve dividir 360 (padrão: 60)")
    ap.add_argument("--distancias", type=int, help="número de polos por raio (padrão: 2)")
    ap.add_argument("--passo-radial", type=float, help="distância entre polos de um raio (padrão: 1)")
    ap.add_argument("--saida", type=Path, help="pasta de saída (padrão: resultado/execucao)")
    ap.add_argument("--relatorio", action="store_true", help="gera o relatório em PDF (resultado/relatorio_momentos.pdf)")
    ap.add_argument("--site", action="store_true", help="exporta os dados do site interativo (docs/momentfield/data)")
    ap.add_argument("--todos", action="store_true", help="os dois casos prontos, o relatório e os dados do site")
    return ap


def config_from(args: argparse.Namespace, base: SamplingConfig) -> SamplingConfig:
    return SamplingConfig(
        n_planes=args.planos if args.planos is not None else base.n_planes,
        plane_spacing=args.espacamento if args.espacamento is not None else base.plane_spacing,
        angle_step_deg=args.passo_angular if args.passo_angular is not None else base.angle_step_deg,
        n_radii=args.distancias if args.distancias is not None else base.n_radii,
        radius_step=args.passo_radial if args.passo_radial is not None else base.radius_step,
    )


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        if args.site or args.todos:
            from .site import export_site

            print(f"dados do site gravados em {export_site() / 'data'}")
        if args.todos:
            for key, case in CASES.items():
                print(f"--- {case.title}")
                run(case.force_point, case.force, case.config, ROOT / "resultado" / key)
        if args.relatorio or args.todos:
            from .relatorio import build_report

            build_report(ROOT / "resultado" / "relatorio_momentos.pdf")
        if args.site or args.relatorio or args.todos:
            return 0

        if args.caso:
            case = CASES[args.caso]
            run(case.force_point, case.force, config_from(args, case.config),
                args.saida or ROOT / "resultado" / args.caso)
            return 0
        force_point = np.array(args.P) if args.P else ask_vector("Ponto de aplicação P", "1 0 2")
        force = np.array(args.F) if args.F else ask_vector("Força F", "2 1 -1.5")
        run(force_point, force, config_from(args, SamplingConfig()), args.saida or ROOT / "resultado" / "execucao")
        return 0
    except InputError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
