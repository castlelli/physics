# Redução de um sistema de forças · `wrench`

Dadas n ≥ 1 forças F_i aplicadas em pontos P_i de um corpo rígido, dois polos Q e A e um versor u,
o programa calcula:

- a) a resultante R = Σ F_i;
- b) o momento M_Q = Σ (P_i − Q) ∧ F_i;
- c) o momento M_A = M_Q + (Q − A) ∧ R;
- d) o torque no eixo Au, M_A · u;
- e) o invariante escalar I = R · M;
- f) a classificação: nulo, redutível a um binário, a uma única força ou a força + binário, e,
  com duas ou mais forças, se elas são paralelas, concorrentes ou coplanares;
- g) quando R ≠ 0, o eixo central (o ponto E mais próximo de Q e a direção de R) e o momento
  mínimo M_E = (I / |R|²) R;

e desenha duas figuras: a 1 com Oxyz, as forças, Q, o eixo Au, R, M_Q e M_A; a 2 com o eixo central
e R e M_E sobre ele. Os pontos ficam numa caixa a × b × c com um vértice em O.

Versão interativa, com o mesmo cálculo no navegador:
<https://castlelli.github.io/physics/wrench/> (em inglês: <https://castlelli.github.io/physics/wrench/en/>)

## Como rodar

```bash
# Ambiente (uma vez só; sem sudo)
micromamba create -y -p ~/.local/envs/pme3100 -c conda-forge python=3.12 numpy matplotlib pytest mscorefonts
PY=~/.local/envs/pme3100/bin/python

cd wrench

# Testes (o de paridade com o site precisa do Node; sem ele é pulado)
$PY -m pytest -q

# Pergunta os dados na ordem do enunciado: n, F_i e P_i, Q, A, u
$PY -m codigo

# Um exemplo pronto (lista com --help)
$PY -m codigo --caso forca_binario

# Dados num arquivo JSON
$PY -m codigo --arquivo dados.json

# Todos os exemplos e os dados do site
$PY -m codigo --todos
```

O arquivo JSON tem `forces` e `points` (listas de vetores), `Q`, `A`, `u` e, opcional, `box: [a, b, c]`.
Cada execução imprime a tabela de resultados e grava em `resultado/<caso>/` (ou em `--saida`)
`figura1.pdf`, `figura2.pdf` (quando há eixo central) e `tabela.csv`.

## Exemplos

| caso | sistema |
|---|---|
| `nulo_par`, `nulo_concorrentes` | nulo |
| `binario_arestas`, `binario_duplo` | redutível a um binário |
| `forca_geral`, `forca_concorrentes`, `forca_coplanares`, `forca_paralelas`, `uma_forca` (n = 1) | redutível a uma única força |
| `forca_binario` | redutível a força + binário |

## Estrutura

- `codigo/modelo.py`: a redução, a classificação e a forma das forças. Sem desenho e sem arquivos.
  As decisões "é zero?" usam tolerâncias relativas à escala dos dados.
- `codigo/casos.py`: os exemplos, cada um com a categoria para a qual foi montado.
- `codigo/figuras.py`, `codigo/estilo.py`: as figuras 1 e 2.
- `codigo/cli.py`: a linha de comando e a tabela. `codigo/site.py`: grava `../docs/wrench/data/golden.json`.
- `tests/`: afirmações físicas (I igual em todo polo, transporte de momentos, momento mínimo no eixo
  central, |M(P)|² = |M_E|² + |R|² d², cada exemplo na sua categoria) e `test_paridade.py`, que roda
  `paridade.mjs` e compara o `model.js` do site com o `golden.json` com tolerância de 1e-12.
- `../docs/wrench/`: o site (HTML, CSS e JavaScript puros, sem etapa de build).
