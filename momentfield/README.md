# Campo de momentos de uma força · PME3100 Mecânica I, Optativa 1

Uma força F aplicada em P tem, em relação a um polo O, o momento M(O) = (P − O) ∧ F. O programa
desenha esse campo sobre polos em planos normais à linha de ação, igualmente espaçados, com raios a
60°, e prova que ele é axissimétrico em torno da linha de ação: pela álgebra (M(O) = F ∧ d), por
três vistas (perspectiva, corte normal ao eixo e corte que contém o eixo) e numericamente.

Versão interativa, com o mesmo cálculo no navegador:
<https://castlelli.github.io/physics/momentfield/> (em inglês: <https://castlelli.github.io/physics/momentfield/en/>)

O relatório é `resultado/relatorio_momentos.pdf`.

## Como rodar

```bash
# Ambiente (uma vez só; sem sudo)
micromamba create -y -p ~/.local/envs/pme3100 -c conda-forge \
    python=3.12 numpy matplotlib jinja2 pytest tectonic mscorefonts
PY=~/.local/envs/pme3100/bin/python

cd momentfield

# Testes (o de paridade com o site precisa do Node; sem ele é pulado)
$PY -m pytest -q

# Pergunta P e F
$PY -m codigo

# Dados na linha de comando
$PY -m codigo --P 1 0 2 --F 2 1 -1.5

# Um caso pronto: relatorio ou campo1 (o exemplo do professor, F = (1, 2, 3) na origem)
$PY -m codigo --caso campo1

# Tudo: os dois casos, o PDF e os dados do site
$PY -m codigo --todos
```

Cada execução grava em `resultado/` (ou em `--saida`) as quatro figuras (`perspectiva.pdf`,
`corte_normal.pdf`, `corte_axial.pdf`, `inclinada.pdf`) e os polos em `amostras.json`, e imprime a
verificação numérica. Na primeira compilação do PDF, o tectonic baixa os pacotes LaTeX.

## Opções

| opção | significado |
|---|---|
| `--P Px Py Pz`, `--F Fx Fy Fz` | ponto de aplicação e força |
| `--caso` | `relatorio` ou `campo1` |
| `--planos`, `--espacamento` | número de planos normais à linha de ação e distância entre eles |
| `--passo-angular` | ângulo entre raios, em graus; deve dividir 360 (o enunciado pede 60) |
| `--distancias`, `--passo-radial` | polos por raio e distância entre eles |
| `--saida` | pasta de saída |
| `--relatorio`, `--site`, `--todos` | PDF, dados do site, ou os dois mais os casos prontos |

## Estrutura

- `codigo/modelo.py`: a matemática (base adaptada à linha de ação, decomposição O − P = s u + d,
  campo, amostragem e cortes). Sem desenho e sem arquivos.
- `codigo/verificacao.py`: as quatro propriedades da axissimetria em polos sorteados.
- `codigo/figuras.py`, `codigo/estilo.py`: figuras com as cores do enunciado.
- `codigo/relatorio.py`, `codigo/templates/`: o PDF. A geração para se um resultado deixar de
  sustentar uma frase do texto (`check_claims`).
- `codigo/site.py`: grava `golden.json` e `report.json` em `../docs/momentfield/data/`.
- `tests/`: cada teste é uma afirmação física ou numérica. `test_paridade.py` roda
  `paridade.mjs`, que compara o `model.js` do site com o `golden.json` com tolerância de 1e-12.
- `../docs/momentfield/`: o site (HTML, CSS e JavaScript puros, sem etapa de build). `js/model.js`
  repete `modelo.py`; `js/scene.js` desenha em 3D num canvas 2D. Para ver localmente:
  `python -m http.server` dentro de `docs/`.
