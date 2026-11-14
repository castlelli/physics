"""Command line: one case writes the figures and the table; a JSON file works; bad input exits with an error."""

import json

from codigo.cli import main


def test_force_couple_case_writes_both_figures_and_the_table(tmp_path, capsys):
    assert main(["--caso", "forca_binario", "--saida", str(tmp_path)]) == 0
    assert {p.name for p in tmp_path.iterdir()} == {"figura1.pdf", "figura2.pdf", "tabela.csv"}
    out = capsys.readouterr().out
    assert "redutível a força + binário" in out and "momento mínimo M_E" in out


def test_couple_has_no_second_figure(tmp_path, capsys):
    assert main(["--caso", "binario_duplo", "--saida", str(tmp_path)]) == 0
    assert not (tmp_path / "figura2.pdf").exists()
    assert "figura 2 não se aplica" in capsys.readouterr().out


def test_json_input_and_point_outside_the_box(tmp_path, capsys):
    data = {"forces": [[0, 0, -1]], "points": [[5, 0, 0]], "Q": [0, 0, 0], "A": [1, 1, 1], "u": [0, 0, 2]}
    path = tmp_path / "dados.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--arquivo", str(path), "--saida", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert "fora da caixa" in out and "redutível a uma única força" in out


def test_zero_u_exits_with_error(tmp_path, capsys):
    data = {"forces": [[1, 0, 0]], "points": [[0, 0, 0]], "Q": [0, 0, 0], "A": [1, 1, 1], "u": [0, 0, 0]}
    path = tmp_path / "dados.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--arquivo", str(path), "--saida", str(tmp_path / "out")]) == 2
    assert "versor" in capsys.readouterr().err
