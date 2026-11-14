"""Ready-made inputs: the professor's Matlab example (Campo1.pdf) and the one used in the report."""

from __future__ import annotations

from dataclasses import dataclass

from .modelo import SamplingConfig


@dataclass(frozen=True)
class Case:
    title: str  # shown to the reader (pt-BR)
    force_point: tuple[float, float, float]
    force: tuple[float, float, float]
    config: SamplingConfig


CASES: dict[str, Case] = {
    "relatorio": Case(
        title="Exemplo do relatório",
        force_point=(1.0, 0.0, 2.0),
        force=(2.0, 1.0, -1.5),
        config=SamplingConfig(n_planes=3, plane_spacing=1.5, angle_step_deg=60.0, n_radii=2, radius_step=1.0),
    ),
    "campo1": Case(
        title="Exemplo do professor (Campo1)",
        force_point=(0.0, 0.0, 0.0),
        force=(1.0, 2.0, 3.0),
        config=SamplingConfig(n_planes=5, plane_spacing=1.0, angle_step_deg=60.0, n_radii=3, radius_step=0.75),
    ),
}

# Reference configuration of the parity fixture (golden.json). Moving it means regenerating the
# fixture with `python -m codigo --site` and rerunning tests/test_paridade.py.
GOLDEN_FORCE_POINT = (1.0, -0.5, 2.0)
GOLDEN_FORCE = (2.0, 1.0, -1.5)
GOLDEN_CONFIG = SamplingConfig(n_planes=3, plane_spacing=1.5, angle_step_deg=60.0, n_radii=2, radius_step=1.0)
