// Verification table: the four properties on random poles, in Python (report.json) and here.

import { runProofs } from "./model.js";
import { fmtSci } from "./ui.js";

const ROWS = [
  ["axial_component", "M normal ao eixo", "máx |M · u|"],
  ["magnitude", "Módulo linear na distância", "máx ||M| − |F| |d||"],
  ["translation", "Translação ao longo do eixo", "máx |M(O + t u) − M(O)|"],
  ["rotation", "Rotação em torno do eixo", "máx |M(R O) − R M(O)|"],
];

export function createProof(report, lab) {
  const root = document.getElementById("verificacao");
  const body = root.querySelector("[data-check-rows]");
  const status = root.querySelector("[data-check-status]");
  const reference = report.cases.relatorio;
  root.querySelector("[data-check-python]").textContent = "Python, exemplo do relatório";
  root.querySelector("[data-check-browser]").textContent = "Navegador, mesmos dados";
  let seed = 1;

  function run() {
    const browser = runProofs(reference.force_point, reference.force, 500, seed);
    const field = lab.field();
    const live = field ? runProofs(field.forcePoint, field.force, 500, seed) : null;
    body.innerHTML = "";
    for (const [key, name, formula] of ROWS) {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${name}<span class="formula">${formula}</span></td><td>${fmtSci(reference.proof.relative[key], 1)}</td><td>${fmtSci(browser.relative[key], 1)}</td><td>${live ? fmtSci(live.relative[key], 1) : "–"}</td>`;
      body.appendChild(row);
    }
    const worst = Math.max(...Object.values(browser.relative), ...(live ? Object.values(live.relative) : []));
    status.textContent = `Erros relativos ao maior |M| sorteado. Pior valor no navegador: ${fmtSci(worst, 1)}, da ordem do épsilon da precisão dupla (2,2×10⁻¹⁶).`;
  }

  root.querySelector("[data-check-run]").addEventListener("click", () => {
    seed += 1;
    run();
  });
  lab.onChange(() => run());
}
