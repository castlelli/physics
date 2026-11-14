// Moment field of a single force: M(O) = (P − O) ∧ F = F ∧ d (Capítulo 1).
// Same math, same order of operations and same sample layout as momentfield/codigo/modelo.py;
// momentfield/tests/test_paridade.py checks both against data/golden.json.

export const ZERO_FORCE_TOL = 1e-12;
const BASIS_CONTINUITY_TOL = 1e-8;

export class InputError extends Error {}

// ---------------------------------------------------------------- vectors ([x, y, z] arrays)

export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a) => Math.sqrt(dot(a, a));

// ---------------------------------------------------------------- field

// Orthonormal right-handed basis (u, v1, v2), u along F. With prevV1, v1 comes from
// Gram–Schmidt against the previous v1, so the rays do not jump while F is dragged.
export function lineBasis(force, prevV1 = null) {
  const length = norm(force);
  if (!(length >= ZERO_FORCE_TOL)) throw new InputError("A força não pode ser nula: sem força não há linha de ação.");
  const u = scale(force, 1 / length);
  let v1 = null;
  if (prevV1) {
    const candidate = sub(prevV1, scale(u, dot(prevV1, u)));
    const candidateNorm = norm(candidate);
    if (candidateNorm > BASIS_CONTINUITY_TOL) v1 = scale(candidate, 1 / candidateNorm);
  }
  if (!v1) {
    // least-aligned coordinate axis gives the best-conditioned cross product (first one on ties, like numpy.argmin)
    const magnitudes = u.map(Math.abs);
    const axis = magnitudes.indexOf(Math.min(...magnitudes));
    const e = [0, 0, 0];
    e[axis] = 1;
    const c = cross(u, e);
    v1 = scale(c, 1 / norm(c));
  }
  return { u, v1, v2: cross(u, v1) };
}

export function moment(pole, forcePoint, force) {
  return cross(sub(forcePoint, pole), force);
}

// Axial offset s, radial part d, distance |d| and foot Q of one pole.
export function decompose(pole, forcePoint, u) {
  const relative = sub(pole, forcePoint);
  const s = dot(relative, u);
  const d = sub(relative, scale(u, s));
  return { s, d, distance: norm(d), foot: add(forcePoint, scale(u, s)) };
}

// Rodrigues rotation of vector v by theta about the unit vector u.
export function rotate(v, u, theta) {
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  return add(add(scale(v, c), scale(cross(u, v), s)), scale(u, dot(u, v) * (1 - c)));
}

// ---------------------------------------------------------------- sampling

export function checkConfig(config) {
  const { nPlanes, planeSpacing, angleStepDeg, nRadii, radiusStep } = config;
  if (!(Number.isInteger(nPlanes) && nPlanes >= 1)) throw new InputError("É preciso ao menos 1 plano.");
  if (!(planeSpacing > 0)) throw new InputError("O espaçamento entre planos deve ser positivo.");
  if (!(Number.isInteger(nRadii) && nRadii >= 1)) throw new InputError("É preciso ao menos 1 distância por raio.");
  if (!(radiusStep > 0)) throw new InputError("O passo radial deve ser positivo.");
  if (!(angleStepDeg > 0) || 360 % angleStepDeg !== 0) throw new InputError("O passo angular deve dividir 360° exatamente.");
  return { ...config, nRays: Math.round(360 / angleStepDeg) };
}

// Poles O = P + s·u + r·(cos θ·v1 + sin θ·v2), ordered plane → ray → radius (numpy meshgrid, indexing="ij").
export function sampleField(config, forcePoint, force, prevV1 = null) {
  const cfg = checkConfig(config);
  const basis = lineBasis(force, prevV1);
  const { u, v1, v2 } = basis;
  const planeOffsets = [];
  for (let i = 0; i < cfg.nPlanes; i++) planeOffsets.push((i - (cfg.nPlanes - 1) / 2) * cfg.planeSpacing);

  const samples = [];
  for (let i = 0; i < cfg.nPlanes; i++) {
    for (let j = 0; j < cfg.nRays; j++) {
      const theta = ((j * cfg.angleStepDeg) * Math.PI) / 180;
      for (let k = 0; k < cfg.nRadii; k++) {
        const r = (k + 1) * cfg.radiusStep;
        const s = planeOffsets[i];
        const pole = add(add(add(forcePoint, scale(u, s)), scale(v1, r * Math.cos(theta))), scale(v2, r * Math.sin(theta)));
        const parts = decompose(pole, forcePoint, u);
        samples.push({
          pole,
          moment: moment(pole, forcePoint, force),
          foot: parts.foot,
          axialOffset: parts.s,
          radialDistance: parts.distance,
          plane: i,
          ray: j,
          radius: k,
        });
      }
    }
  }
  return { config: cfg, forcePoint, force, basis, planeOffsets, samples };
}

// Sections are data filters over the sampled poles, never camera angles.
export function normalSection(field, plane = Math.floor(field.config.nPlanes / 2)) {
  return field.samples.filter((sample) => sample.plane === plane);
}

// Poles in the plane that contains the axis and v1: rays at 0° and, if sampled, 180°.
export function axialSection(field) {
  const opposite = field.config.nRays % 2 === 0 ? field.config.nRays / 2 : -1;
  return field.samples.filter((sample) => sample.ray === 0 || sample.ray === opposite);
}

// Largest drawn moment at 60 % of the largest radius, drawn force at 80 % (same as figuras.auto_scale).
export function autoScale(field) {
  const maxRadius = Math.max(...field.samples.map((s) => s.radialDistance));
  const maxMoment = Math.max(...field.samples.map((s) => norm(s.moment)));
  return { moment: maxMoment > 0 ? (0.6 * maxRadius) / maxMoment : 1, force: (0.8 * maxRadius) / norm(field.force) };
}

// ---------------------------------------------------------------- proofs

// Small seeded generator (mulberry32), so a run can be repeated.
export function random(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The four properties of verificacao.py on random poles; errors relative to the largest |M|.
export function runProofs(forcePoint, force, nPoles = 500, seed = 1) {
  const { u } = lineBasis(force);
  const next = random(seed);
  const uniform = (lo, hi) => lo + (hi - lo) * next();
  const theta = uniform(0, 2 * Math.PI);
  const normF = norm(force);
  let axial = 0;
  let magnitude = 0;
  let translation = 0;
  let rotation = 0;
  let biggest = 0;
  for (let n = 0; n < nPoles; n++) {
    const pole = add(forcePoint, [uniform(-5, 5), uniform(-5, 5), uniform(-5, 5)]);
    const m = moment(pole, forcePoint, force);
    const size = norm(m);
    biggest = Math.max(biggest, size);
    axial = Math.max(axial, Math.abs(dot(m, u)));
    magnitude = Math.max(magnitude, Math.abs(size - normF * decompose(pole, forcePoint, u).distance));
    const shifted = moment(add(pole, scale(u, uniform(-10, 10))), forcePoint, force);
    translation = Math.max(translation, norm(sub(shifted, m)));
    const turned = moment(add(forcePoint, rotate(sub(pole, forcePoint), u, theta)), forcePoint, force);
    rotation = Math.max(rotation, norm(sub(turned, rotate(m, u, theta))));
  }
  const k = biggest || 1;
  return { nPoles, relative: { axial_component: axial / k, magnitude: magnitude / k, translation: translation / k, rotation: rotation / k } };
}
