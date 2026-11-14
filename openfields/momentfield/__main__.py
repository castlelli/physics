"""CLI: reads P and F, verifies the axisymmetry numerically, writes the report PDF.

Run as ``python -m momentfield``. All user-facing text is Portuguese (pt-BR).
"""

from __future__ import annotations

import argparse
import sys

import matplotlib

matplotlib.use("Agg")  # headless: the CLI only writes files, never opens a window

import numpy as np

from momentfield.export import write_field_json
from momentfield.proofs import ProofReport, run_proofs
from momentfield.render_mpl import auto_render_options, make_report_pdf
from momentfield.sampling import SamplingConfig, sample_field


def _parse_vector(text: str) -> np.ndarray:
    parts = text.replace(",", " ").split()
    if len(parts) != 3:
        raise ValueError("são necessárias exatamente 3 componentes")
    return np.array([float(part) for part in parts], dtype=float)


def _prompt_vector(label: str, example: str) -> np.ndarray:
    while True:
        try:
            return _parse_vector(input(f"{label} (ex.: {example}): "))
        except ValueError:
            print("  Entrada inválida — digite 3 números separados por espaço.")


def _format_report(report: ProofReport) -> list[str]:
    def line(name: str, value: float) -> str:
        status = "OK" if value < report.tolerance else "FALHOU"
        return f"{name}: {value:.3e}  [{status}]"

    return [
        f"({report.n_poles} polos aleatórios, tolerância {report.tolerance:.0e})",
        line("máx |M·u| (M normal ao eixo)", report.max_axial_component),
        line("máx ||M| − |F|·|d|| (módulo linear em |d|)", report.max_magnitude_error),
        line("máx |M(O + t·u) − M(O)| (invariância axial)", report.max_translation_error),
        line("máx |M(R·O) − R·M(O)| (equivariância rotacional)", report.max_rotation_error),
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m momentfield",
        description=(
            "Campo de momentos de uma força: M(O) = (P − O) ∧ F. "
            "Gera um PDF com vistas em perspectiva e as duas seções que "
            "demonstram a axissimetria em torno da linha de ação."
        ),
    )
    parser.add_argument("--ponto", type=str, default=None, metavar='"Px Py Pz"',
                        help="ponto de aplicação P (se omitido, será perguntado)")
    parser.add_argument("--forca", type=str, default=None, metavar='"Fx Fy Fz"',
                        help="força F (se omitida, será perguntada)")
    parser.add_argument("--saida", type=str, default="campo_de_momentos.pdf",
                        help="arquivo PDF de saída (padrão: %(default)s)")
    parser.add_argument("--planos", type=int, default=3,
                        help="número de planos normais à linha de ação (padrão: %(default)s)")
    parser.add_argument("--espacamento", type=float, default=1.5,
                        help="espaçamento entre planos (padrão: %(default)s)")
    parser.add_argument("--passo-angular", type=float, default=60.0,
                        help="passo angular entre raios, em graus; deve dividir 360 "
                             "(padrão: %(default)s)")
    parser.add_argument("--aneis", type=int, default=2,
                        help="número de distâncias radiais por raio (padrão: %(default)s)")
    parser.add_argument("--passo-radial", type=float, default=1.0,
                        help="passo entre distâncias radiais (padrão: %(default)s)")
    parser.add_argument("--escala-momento", type=float, default=None,
                        help="fator de escala para desenhar M(O) (padrão: automático)")
    parser.add_argument("--json", type=str, default=None, metavar="ARQUIVO",
                        help="também exporta as amostras no contrato JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    print("Campo de momentos de uma força — M(O) = (P − O) ∧ F")
    try:
        point = _parse_vector(args.ponto) if args.ponto else _prompt_vector(
            "Ponto de aplicação P", "1 0 2"
        )
        if args.forca:
            force = _parse_vector(args.forca)
        else:
            force = _prompt_vector("Força F", "0 0 5")
            while float(np.linalg.norm(force)) == 0.0:
                print("  A força não pode ser nula — a linha de ação fica indefinida.")
                force = _prompt_vector("Força F", "0 0 5")
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    if float(np.linalg.norm(force)) == 0.0:
        print("Erro: a força não pode ser nula — a linha de ação fica indefinida.",
              file=sys.stderr)
        return 2

    try:
        config = SamplingConfig(
            n_planes=args.planos,
            plane_spacing=args.espacamento,
            angle_step_deg=args.passo_angular,
            n_radii=args.aneis,
            radius_step=args.passo_radial,
        )
    except ValueError as error:
        print(f"Erro na configuração da amostragem: {error}", file=sys.stderr)
        return 2

    field = sample_field(config, point, force)

    print("\nVerificação numérica da axissimetria:")
    report = run_proofs(point, force)
    verification_lines = _format_report(report)
    for line in verification_lines:
        print(f"  {line}")
    if not report.passed:
        print("Atenção: alguma verificação excedeu a tolerância.", file=sys.stderr)

    options = auto_render_options(field)
    if args.escala_momento is not None:
        options = type(options)(moment_scale=args.escala_momento,
                                force_scale=options.force_scale)

    print("\nGerando figuras (perspectivas + seção normal + seção axial)...")
    make_report_pdf(field, args.saida, options=options,
                    verification_lines=verification_lines)
    print(f"PDF salvo em: {args.saida}")

    if args.json:
        write_field_json(field, args.json)
        print(f"Amostras exportadas em: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
