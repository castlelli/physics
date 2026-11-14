"""Ready-made systems on a 2 × 1,5 × 1 box: every category of the statement, and for 'single force'
the general, concurrent, coplanar and parallel kinds, plus n = 1. Where there is a central axis, the
data were chosen so that it crosses the box (tests/test_modelo.py checks it); the physics alone
does not require that."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .modelo import (
    CONCURRENT,
    COPLANAR,
    COUPLE,
    FORCE_COUPLE,
    NULL,
    PARALLEL,
    SINGLE_FORCE,
    Box,
    System,
)

BOX = Box(2.0, 1.5, 1.0)
ORIGIN = (0.0, 0.0, 0.0)
FAR_CORNER = (2.0, 1.5, 1.0)


@dataclass(frozen=True)
class Case:
    title: str  # pt-BR, shown in the CLI and the figures
    forces: tuple[tuple[float, float, float], ...]
    points: tuple[tuple[float, float, float], ...]
    pole_q: tuple[float, float, float]
    pole_a: tuple[float, float, float]
    u: tuple[float, float, float]
    expected: str  # category the case was built to have
    expected_shape: tuple[str, ...] = ()
    view: tuple[float, float] = (24.0, -58.0)  # elevation, azimuth of the figures

    def system(self) -> System:
        return System(np.array(self.forces), np.array(self.points), np.array(self.pole_q),
                      np.array(self.pole_a), np.array(self.u), BOX)


CASES: dict[str, Case] = {
    "nulo_par": Case(
        title="Nulo: duas forças opostas na mesma reta",
        forces=((3.0, 0.0, 0.0), (-3.0, 0.0, 0.0)),
        points=((0.0, 0.75, 0.5), (2.0, 0.75, 0.5)),
        pole_q=ORIGIN, pole_a=FAR_CORNER, u=(0.0, 0.0, 1.0),
        expected=NULL, expected_shape=(PARALLEL, COPLANAR),
    ),
    "nulo_concorrentes": Case(
        title="Nulo: três forças num vértice, de soma zero",
        forces=((-2.0, 0.0, 1.0), (1.0, -2.0, 0.0), (1.0, 2.0, -1.0)),
        points=(FAR_CORNER, FAR_CORNER, FAR_CORNER),
        pole_q=ORIGIN, pole_a=(2.0, 0.0, 0.0), u=(0.0, 1.0, 0.0),
        expected=NULL, expected_shape=(CONCURRENT, COPLANAR),
    ),
    "binario_arestas": Case(
        title="Binário: forças opostas em arestas paralelas",
        forces=((0.0, 2.0, 0.0), (0.0, -2.0, 0.0)),
        points=((0.0, 0.0, 1.0), (2.0, 0.0, 0.0)),
        pole_q=ORIGIN, pole_a=FAR_CORNER, u=(1.0, 0.0, 0.0),
        expected=COUPLE, expected_shape=(PARALLEL, COPLANAR),
    ),
    "binario_duplo": Case(
        title="Binário: dois binários em planos diferentes",
        forces=((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 2.0), (0.0, 0.0, -2.0)),
        points=((0.0, 0.0, 0.0), (0.0, 1.5, 0.0), (2.0, 0.0, 0.0), (2.0, 1.5, 0.0)),
        pole_q=(1.0, 0.75, 0.5), pole_a=FAR_CORNER, u=(0.0, 0.0, 1.0),
        expected=COUPLE,
    ),
    "forca_geral": Case(
        title="Uma força: peso no topo e um binário perpendicular",
        forces=((0.0, 0.0, -3.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)),
        points=((1.0, 0.75, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        pole_q=ORIGIN, pole_a=FAR_CORNER, u=(0.0, 1.0, 0.0),
        expected=SINGLE_FORCE,
    ),
    "forca_concorrentes": Case(
        title="Uma força: forças concorrentes no centro da caixa",
        forces=((0.0, 0.0, -2.0), (1.5, 0.0, 0.0), (0.0, 1.0, 0.0)),
        points=((1.0, 0.75, 1.0), (0.0, 0.75, 0.5), (1.0, 0.0, 0.5)),
        pole_q=ORIGIN, pole_a=(2.0, 1.5, 0.0), u=(1.0, 1.0, 0.0),
        expected=SINGLE_FORCE, expected_shape=(CONCURRENT,),
    ),
    "forca_coplanares": Case(
        title="Uma força: forças coplanares na face superior",
        forces=((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, -1.0, 0.0)),
        points=((0.0, 0.25, 1.0), (0.5, 0.0, 1.0), (2.0, 1.5, 1.0)),
        pole_q=ORIGIN, pole_a=(0.0, 1.5, 1.0), u=(0.0, 0.0, 1.0),
        expected=SINGLE_FORCE, expected_shape=(COPLANAR,),
        view=(38.0, -64.0),
    ),
    "forca_paralelas": Case(
        title="Uma força: pesos paralelos sobre a face superior",
        forces=((0.0, 0.0, -1.0), (0.0, 0.0, -2.0), (0.0, 0.0, -1.5)),
        points=((0.5, 0.5, 1.0), (1.5, 0.5, 1.0), (1.0, 1.25, 1.0)),
        pole_q=ORIGIN, pole_a=(2.0, 0.0, 0.0), u=(0.0, 1.0, 0.0),
        expected=SINGLE_FORCE, expected_shape=(PARALLEL,),
    ),
    "uma_forca": Case(
        title="Uma força: n = 1",
        forces=((1.0, -0.5, -2.0),),
        points=((1.0, 0.75, 1.0),),
        pole_q=ORIGIN, pole_a=(0.0, 1.5, 1.0), u=(1.0, 0.0, 0.0),
        expected=SINGLE_FORCE,
    ),
    "forca_binario": Case(
        title="Força e binário: três forças quaisquer",
        forces=((0.0, 2.0, 0.0), (0.0, 0.0, 3.0), (1.0, 0.0, -1.0)),
        points=((0.0, 0.0, 1.0), (2.0, 0.75, 0.0), (2.0, 0.75, 0.5)),
        pole_q=ORIGIN, pole_a=FAR_CORNER, u=(1.0, 1.0, 1.0),
        expected=FORCE_COUPLE,
    ),
}
