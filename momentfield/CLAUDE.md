# CLAUDE.md

Persistent project context. Read this fully before any task in this repository.

## Project

Interactive visualizer for the **moment field of a single force** — coursework for Mecânica I (Escola Politécnica da USP, Prof. Flavius P. R. Martins).

Given a force `F = (Fx, Fy, Fz)` applied at a point `P = (Px, Py, Pz)`, the program draws the field `M(O) = (P − O) ∧ F` over sampled poles `O`, and must **demonstrate that the field is axisymmetric about the line of action of F**.

This is an academic deliverable. Correctness of the geometry and the ability to defend it outrank feature count, cleverness, and visual polish.

## Ground truth — the math that drives every design decision

Let `u = F/|F|`. Decompose `(O − P) = s·u + d`, where `s = (O − P)·u` and `d ⊥ u`.

```
M(O) = (P − O) ∧ F = −(s·u + d) ∧ F = F ∧ d
```

Consequences that MUST hold in any implementation and MUST NOT be re-derived differently:

- `M(O)` is independent of `s` — it depends only on the position relative to the axis. **This is the axisymmetry.**
- `|M| = |F| · |d|` — magnitude grows linearly with distance from the axis.
- `M ⊥ u` and `M ⊥ d` — therefore `O`, `Q` (foot of the perpendicular from `O` onto the line of action), and the tip of `M(O)` are **coplanar**, all lying in the plane Π normal to the line of action through `O`. The triangle `O–Q–tip(M)` is right-angled at `O`.
- The computation is closed-form, allocation-light, and vectorizable. There is no solver, no integration, no iteration. If a proposed design needs a server round-trip or a worker thread to compute this, the design is wrong.

## Hard requirements (from the assignment statement — do not alter)

1. Force `F` and its line of action drawn in **red**.
2. Moment vectors `M(O)` drawn in **black**.
3. **Green** dashed lines from each `O` to its `Q`.
4. **Blue** dashed lines from the tip of each `M(O)` to the same `Q`.
5. Poles `O` lie on planes **normal to the line of action, equally spaced**.
6. Within each plane, the rays `Q → O` are separated by **60°** — i.e. 6 rays per plane. Parametrize as `angleStepDeg` and derive `nRays = 360 / angleStepDeg`; validate divisibility.

## Hard requirements (from the professor's clarification email — do not drop)

The program must **prove** the axisymmetry, not merely suggest it. Three views are required:

| View | Data filter | Expected appearance |
|---|---|---|
| Perspective | none | full field, arbitrary observer position |
| Section ⊥ to axis | single plane Π (`\|s − s₀\| < ε`) | pinwheel — tangential `M`, invariant under 60° rotation |
| Section ∥ to axis | plane containing the axis (`\|d·v₂\| < ε`) | `M` normal to the page, magnitude linear in `\|d\|`, sign flipping across the axis |

**A section is a data filter, not a camera angle.** Rotating the camera while still rendering every sample produces clutter that does not demonstrate anything. Filter the sample set, then orient the camera.

## Architecture — locked decisions

- **Python is the reference implementation.** It owns the math, the static figures for the written report, and the numerical proof harness. It is not scaffolding to be deleted later.
- **The site re-implements the math in plain JavaScript** (`../docs/momentfield/js/model.js`), following the other projects in this repository: HTML, CSS and ES modules, no build step, no libraries. The 3D view is a small orthographic canvas renderer (`js/scene.js`), not WebGL. Not Pyodide, not a backend.
- **Parity is enforced by fixture, not by discipline.** `python -m codigo --site` writes `docs/momentfield/data/golden.json`; `tests/test_paridade.py` runs `tests/paridade.mjs`, which asserts agreement to 1e-12. Any change to the math in one language MUST be accompanied by a regenerated fixture and a passing parity test.
- **One JSON contract** feeds both renderers. Samples carry `plane`, `ray`, and `radius` indices — these exist so the front-end can filter sections and highlight rays without recomputing. Do not strip them as "redundant".

```
codigo/
  modelo.py       # pure math + sampling + section filters, numpy, zero I/O
  verificacao.py  # numerical verification of axisymmetry
  estilo.py       # Times New Roman, statement colours
  figuras.py      # report figures (sections drawn exactly in plane coordinates)
  relatorio.py    # LaTeX report via jinja2 + tectonic; check_claims guards the text
  casos.py        # ready-made inputs and the golden configuration
  site.py         # JSON contract, golden.json, report.json for the site
  cli.py          # `python -m codigo`
```

Module file names follow the sibling projects (duffing, carousel); identifiers and comments stay in English.

## Known pitfalls — check these before declaring a task done

- **Moment vector scale.** `|M|` grows with both radius and `|F|`; unscaled vectors overwhelm the figure. Expose a `momentScale` control. The blue lines run to the *drawn* (scaled) tip, so the triangle preserves perpendicularity but not metric length — this trade-off MUST be stated in the figure legend.
- **Equal aspect ratio is mandatory.** `ax.set_box_aspect((1,1,1))` plus symmetric limits in matplotlib; one scale for all three axes in `scene.js`. Without it, right angles render skewed and the figure visually contradicts the proof it exists to make.
- **Orthonormal basis stability.** Choosing `v1 = u × (least-aligned axis)` is correct but discontinuous — the rays jump when `F` crosses a threshold during dragging. Cache the basis and re-orthogonalize against the previous `v1` (Gram–Schmidt) rather than recomputing from scratch.
- **matplotlib 3D has no true z-sorting.** Back vectors draw over front ones. The report draws the two sections as exact 2D plots in plane coordinates for this reason; the site's renderer sorts by depth.
- **Degenerate inputs.** `F = 0`, and `O` on the axis (`d = 0`, so `M = 0` with no defined radial direction). Handle explicitly before `NaN` reaches the renderer.

## Engineering standards

- **Correctness first, then clarity, then performance.** This code exists to be defended to an examiner. Prefer the formulation that is easiest to check against the lecture notes over the one that is fastest.
- **Separate computation from presentation.** `modelo.py` and `verificacao.py` MUST NOT import matplotlib or touch the filesystem. Rendering modules consume plain arrays and dataclasses.
- **Pure functions and immutable inputs by default.** No hidden global state, no mutation of caller-owned arrays.
- **Vectorize with numpy; no Python loops over sample points.** Loops over planes or rays during construction are fine.
- **Type hints on every public function; dataclasses for structured data.** No bare tuples or dicts crossing module boundaries.
- **Name things after the physics.** `moment`, `pole`, `foot`, `line_of_action`, `axial_offset` — not `vec1`, `tmp`, `calc`.
- **Every non-obvious formula carries a one-line comment citing the source** — e.g. the equation number in the Capítulo 1 lecture notes.
- **Tests are numerical assertions, not smoke tests.** Assert `M·u = 0`, `|M| = |F|·dist(O, axis)`, and rotational equivariance `M(R_θ·O) = R_θ·M(O)` for random θ, to machine precision.
- **No dependency added without asking.** Current allowance: numpy, matplotlib, jinja2, pytest, and tectonic + mscorefonts for the PDF. Anything else requires approval.
- **YAGNI.** Do not add configuration, abstraction layers, plugin systems, or generality that no current requirement demands. A second implementation is not an abstraction candidate; a third might be.

## Scope

- Work only in: `codigo/`, `tests/`, `../docs/momentfield/`, and this project's docs.
- Do NOT touch: `.env`, lockfiles, CI configuration, or anything outside the paths above.
- Only make changes directly requested. Do not add features, refactor adjacent code, or create files beyond what was asked.

## Stop conditions

Stop and ask before:

- Deleting any file.
- Adding any dependency.
- Changing the JSON contract shape or the `golden.json` fixture.
- Altering any of the six numbered assignment requirements or the three required views.
- Choosing between two implementation paths where the choice affects the architecture above.
- Retrying a failing approach a third time.

## Progress reporting

After each completed step, output: `✅ [what was done] — [file(s) affected]`.
At the end of a multi-step task, list every file created, modified, or deleted.

## Conventions

- Code, identifiers, comments, commit messages, and this file: **English**.
- Figure titles, axis labels, legends, CLI help text, and anything the professor reads: **Portuguese (pt-BR)**.