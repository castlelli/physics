# Campo de momentos de uma força

Visualizer for the moment field of a single force — coursework for Mecânica I
(Escola Politécnica da USP). Given a force `F` applied at a point `P`, the
program draws `M(O) = (P − O) ∧ F` over sampled poles `O` and demonstrates that
the field is axisymmetric about the line of action of `F`.

This is the Python reference implementation: an interactive CLI that produces a
static PDF report (perspective views plus the two proof sections) and a
numerical verification of the axisymmetry.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

Interactive (asks for `P` and `F` in the shell):

```bash
.venv/bin/python -m momentfield
```

Non-interactive:

```bash
.venv/bin/python -m momentfield --ponto "1 0 2" --forca "2 1 -1.5" --saida campo_de_momentos.pdf
```

Run `.venv/bin/python -m momentfield --help` for the sampling options
(number of planes, spacing, angular step, radii, moment drawing scale) and the
optional JSON export of the samples.

The output PDF contains:

1. a title page with the input data, the sampling layout, the color legend and
   the numerical verification results;
2. perspective views of the full field from several observer positions;
3. the section normal to the line of action (single plane of poles — the
   pinwheel invariant under 60° rotations);
4. the section containing the line of action (moments normal to the page,
   magnitude linear in the distance to the axis), plus a slightly tilted view
   of the same data to make the out-of-page vectors visible.

## Tests

```bash
.venv/bin/python -m pytest tests/
```

The tests are numerical assertions to machine precision: `M · u = 0`,
`|M| = |F| · dist(O, axis)`, invariance under axial translation, rotational
equivariance, sampling layout, and exact round-trip of the JSON contract.
