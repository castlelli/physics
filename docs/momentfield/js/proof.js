// Verification table: the four properties on random poles, in Python (report.json) and here.

import { runProofs } from "./model.js";
import { fmtSci } from "./ui.js";
import { T } from "./i18n.js";

const ROWS = [
  ["axial_component", "|M · u|"],
  ["magnitude", "||M| − |F| |d||"],
  ["translation", "|M(O + t u) − M(O)|"],
  ["rotation", "|M(R O) − R M(O)|"],
];

export function createProof(report, lab) {
  const root = document.getElementById("verificacao");
  const body = root.querySelector("[data-check-rows]");
  const status = root.querySelector("[data-check-status]");
  const reference = report.cases.relatorio;
  root.querySelector("[data-check-python]").textContent = T.proofPython;
  root.querySelector("[data-check-browser]").textContent = T.proofBrowser;
  let seed = 1;

  function run() {
    const browser = runProofs(reference.force_point, reference.force, 500, seed);
    const field = lab.field();
    const live = field ? runProofs(field.forcePoint, field.force, 500, seed) : null;
    body.innerHTML = "";
    for (const [key, formula] of ROWS) {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${T.proofRows[key]}<span class="formula">${T.proofMax} ${formula}</span></td><td>${fmtSci(reference.proof.relative[key], 1)}</td><td>${fmtSci(browser.relative[key], 1)}</td><td>${live ? fmtSci(live.relative[key], 1) : "–"}</td>`;
      body.appendChild(row);
    }
    const worst = Math.max(...Object.values(browser.relative), ...(live ? Object.values(live.relative) : []));
    status.textContent = T.proofStatus(fmtSci(worst, 1), fmtSci(2.220446049250313e-16, 1));
  }

  root.querySelector("[data-check-run]").addEventListener("click", () => {
    seed += 1;
    run();
  });
  lab.onChange(() => run());
}
