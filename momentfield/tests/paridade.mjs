// Parity: docs/momentfield/js/model.js against the fixture Python wrote (data/golden.json).
// Prints the worst absolute difference per quantity; exits 1 if any exceeds 1e-12.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const docs = join(here, "..", "..", "docs", "momentfield");
const { sampleField } = await import(join(docs, "js", "model.js"));
const golden = JSON.parse(readFileSync(join(docs, "data", "golden.json"), "utf-8"));
const c = golden.config;
const field = sampleField(
  { nPlanes: c.n_planes, planeSpacing: c.plane_spacing, angleStepDeg: c.angle_step_deg, nRadii: c.n_radii, radiusStep: c.radius_step },
  golden.force_point,
  golden.force,
);

const worst = {};
const compare = (name, a, b) => {
  const diff = Array.isArray(a) ? Math.max(...a.map((x, i) => Math.abs(x - b[i]))) : Math.abs(a - b);
  worst[name] = Math.max(worst[name] ?? 0, diff);
};
for (const key of ["u", "v1", "v2"]) compare(`basis.${key}`, field.basis[key], golden.basis[key]);
const g = golden.samples;
if (g.poles.length !== field.samples.length) {
  console.log(`número de polos diferente: ${field.samples.length} contra ${g.poles.length}`);
  process.exit(1);
}
field.samples.forEach((s, i) => {
  compare("poles", s.pole, g.poles[i]);
  compare("moments", s.moment, g.moments[i]);
  compare("feet", s.foot, g.feet[i]);
  compare("axial_offset", s.axialOffset, g.axial_offset[i]);
  compare("radial_distance", s.radialDistance, g.radial_distance[i]);
  compare("indices", [s.plane, s.ray, s.radius], [g.plane[i], g.ray[i], g.radius[i]]);
});
for (const [name, value] of Object.entries(worst)) console.log(`${name}: ${value.toExponential(2)}`);
process.exit(Object.values(worst).every((v) => v <= 1e-12) ? 0 : 1);
