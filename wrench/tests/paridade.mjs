// Parity: docs/wrench/js/model.js against the fixture Python wrote (data/golden.json).
// Same category and shape, numbers within 1e-12; prints the worst difference per output; exits 1 on failure.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const docs = join(here, "..", "..", "docs", "wrench");
const { reduce } = await import(join(docs, "js", "model.js"));
const golden = JSON.parse(readFileSync(join(docs, "data", "golden.json"), "utf-8"));

const worst = {};
const problems = [];
const compare = (name, a, b) => {
  if ((a === null) !== (b === null)) return problems.push(`${name}: ${JSON.stringify(a)} contra ${JSON.stringify(b)}`);
  if (a === null) return;
  const diff = Array.isArray(a) ? Math.max(...a.map((x, i) => Math.abs(x - b[i]))) : Math.abs(a - b);
  worst[name] = Math.max(worst[name] ?? 0, diff);
};
for (const [key, item] of Object.entries(golden.cases)) {
  const r = reduce(item.input);
  const g = item.output;
  if (r.category !== g.category) problems.push(`${key}: categoria ${r.category} contra ${g.category}`);
  if (JSON.stringify(r.shape) !== JSON.stringify(g.shape)) problems.push(`${key}: forma ${r.shape} contra ${g.shape}`);
  compare("R", r.R, g.R);
  compare("M_Q", r.MQ, g.M_Q);
  compare("M_A", r.MA, g.M_A);
  compare("unit_u", r.unitU, g.unit_u);
  compare("axis_torque", r.axisTorque, g.axis_torque);
  compare("I", r.I, g.I);
  compare("axis_point", r.axisPoint, g.axis_point);
  compare("axis_direction", r.axisDirection, g.axis_direction);
  compare("M_E", r.ME, g.M_E);
}
for (const [name, value] of Object.entries(worst)) console.log(`${name}: ${value.toExponential(2)}`);
for (const p of problems) console.log(p);
process.exit(problems.length === 0 && Object.values(worst).every((v) => v <= 1e-12) ? 0 : 1);
