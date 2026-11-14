// Verification: every example's intended category against the browser's reduction, the largest
// difference from Python's numbers (golden.json), and random-pole checks on the lab's data.

import { add, cross, dot, momentAbout, norm, random, reduce, sub } from "./model.js";
import { fmtSci } from "./ui.js";
import { T } from "./i18n.js";

const OUTPUTS = [
  ["R", "R"], ["MQ", "M_Q"], ["MA", "M_A"], ["axisTorque", "axis_torque"], ["I", "I"],
  ["axisPoint", "axis_point"], ["axisDirection", "axis_direction"], ["ME", "M_E"],
];

function largestDifference(r, output) {
  let worst = 0;
  for (const [mine, theirs] of OUTPUTS) {
    const a = r[mine];
    const b = output[theirs];
    if (a === null || b === null) continue;
    worst = Math.max(worst, ...(Array.isArray(a) ? a.map((x, i) => Math.abs(x - b[i])) : [Math.abs(a - b)]));
  }
  return worst;
}

export function createProof(golden, lab) {
  const root = document.getElementById("verificacao");
  const body = root.querySelector("[data-check-rows]");
  const status = root.querySelector("[data-check-status]");
  root.querySelector("[data-check-case]").textContent = T.proofCaseHead;
  root.querySelector("[data-check-expected]").textContent = T.proofExpected;
  root.querySelector("[data-check-browser]").textContent = T.proofBrowser;
  root.querySelector("[data-check-diff]").textContent = T.proofDiff;
  let seed = 1;

  body.innerHTML = Object.entries(golden.cases)
    .map(([key, item]) => {
      const r = reduce(item.input);
      const same = r.category === item.expected && JSON.stringify(r.shape) === JSON.stringify(item.output.shape);
      const shape = r.shape.length ? ` (${T.forcesAre(r.shape.map((s) => T.shape[s]).join(", "))})` : "";
      return `<tr><td>${T.cases[key]}</td><td>${T.category[item.expected]}</td><td class="${same ? "ok" : "bad"}">${T.category[r.category]}${shape}</td><td>${fmtSci(largestDifference(r, item.output), 1)}</td></tr>`;
    })
    .join("");

  // Random poles on the lab's system: transport against direct sum, and R · M_P against I.
  function randomChecks() {
    const system = lab.system();
    const r = lab.reduction();
    if (!r) {
      status.textContent = "";
      return;
    }
    const next = random(seed);
    let transport = 0;
    let invariant = 0;
    let biggestM = 1e-300;
    let biggestRM = 1e-300;
    for (let n = 0; n < 500; n++) {
      const pole = [0, 1, 2].map(() => -3 + 6 * next());
      const direct = momentAbout(system, pole);
      const moved = add(r.MQ, cross(sub(system.Q, pole), r.R));
      biggestM = Math.max(biggestM, norm(direct));
      biggestRM = Math.max(biggestRM, norm(r.R) * norm(direct));
      transport = Math.max(transport, norm(sub(direct, moved)));
      invariant = Math.max(invariant, Math.abs(dot(r.R, direct) - r.I));
    }
    status.textContent = T.proofStatus(fmtSci(transport / biggestM, 1), fmtSci(invariant / biggestRM, 1));
  }

  root.querySelector("[data-check-run]").addEventListener("click", () => {
    seed += 1;
    randomChecks();
  });
  lab.onChange(() => randomChecks());
}
