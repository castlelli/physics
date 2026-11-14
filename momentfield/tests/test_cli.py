"""Command line: one run writes the figures and samples; bad input exits with an error."""

import json

from codigo.cli import main


def test_one_run_writes_four_figures_and_the_samples(tmp_path):
    assert main(["--P", "1", "0", "2", "--F", "2", "1", "-1.5", "--saida", str(tmp_path)]) == 0
    names = {p.name for p in tmp_path.iterdir()}
    assert {"perspectiva.pdf", "corte_normal.pdf", "corte_axial.pdf", "inclinada.pdf", "amostras.json"} <= names
    samples = json.loads((tmp_path / "amostras.json").read_text(encoding="utf-8"))
    assert len(samples["samples"]["poles"]) == 36


def test_zero_force_exits_with_error(tmp_path, capsys):
    assert main(["--P", "0", "0", "0", "--F", "0", "0", "0", "--saida", str(tmp_path)]) == 2
    assert "nula" in capsys.readouterr().err


def test_angle_step_that_does_not_divide_360_exits_with_error(tmp_path, capsys):
    assert main(["--caso", "campo1", "--passo-angular", "70", "--saida", str(tmp_path)]) == 2
    assert "360" in capsys.readouterr().err
