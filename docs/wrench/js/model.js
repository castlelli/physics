// Reduction of a system of forces: R, M_Q, M_A, torque about Au, invariant I, category, central axis, M_E.
// Same math, order of operations and decisions as wrench/codigo/modelo.py; wrench/tests/test_paridade.py
// checks both against data/golden.json. No page code here: the parity test runs it under Node.

export const EPS = 1e-9;
export const NULL = "null";
export const COUPLE = "couple";
export const SINGLE_FORCE = "single_force";
export const FORCE_COUPLE = "force_couple";

// The message is a code; the page translates it (js/i18n.js, errors).
export class InputError extends Error {}

export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a) => Math.sqrt(dot(a, a));

export function boxContains(box, p, tol = 1e-9) {
  return p.every((c, i) => c >= -tol * box[i] && c <= box[i] * (1 + tol));
}

// Σ (P_i − pole) ∧ F_i, summed directly over the forces.
export function momentAbout(system, pole) {
  let m = [0, 0, 0];
  system.forces.forEach((f, i) => (m = add(m, cross(sub(system.points[i], pole), f))));
  return m;
}

function lengthScale(system) {
  const pts = [...system.points, system.Q, system.A];
  let largest = 0;
  for (const p of pts) for (const q of pts) largest = Math.max(largest, norm(sub(p, q)));
  return largest > 0 ? largest : 1;
}

export function classify(R, M, I, S, L) {
  const rZero = norm(R) <= EPS * S;
  const mZero = norm(M) <= EPS * S * L;
  if (rZero) return mZero ? NULL : COUPLE;
  return Math.abs(I) <= EPS * norm(R) * S * L ? SINGLE_FORCE : FORCE_COUPLE;
}

// Solve a 3×3 system by Gaussian elimination with partial pivoting.
function solve3(m, b) {
  const a = m.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < 3; c++) {
    let p = c;
    for (let r = c + 1; r < 3; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
    [a[c], a[p]] = [a[p], a[c]];
    for (let r = c + 1; r < 3; r++) {
      const f = a[r][c] / a[c][c];
      for (let k = c; k < 4; k++) a[r][k] -= f * a[c][k];
    }
  }
  const x = [0, 0, 0];
  for (let r = 2; r >= 0; r--) {
    let s = a[r][3];
    for (let k = r + 1; k < 3; k++) s -= a[r][k] * x[k];
    x[r] = s / a[r][r];
  }
  return x;
}

// Which of parallel, concurrent and coplanar the lines of action are (n ≥ 2 non-zero forces).
export function forceShape(system, S, L) {
  const directions = [];
  const points = [];
  system.forces.forEach((f, i) => {
    const n = norm(f);
    if (n > EPS * S) {
      directions.push(scale(f, 1 / n));
      points.push(system.points[i]);
    }
  });
  if (directions.length < 2) return [];
  const shapes = [];
  const parallel = directions.every((d) => norm(cross(d, directions[0])) <= EPS);
  if (parallel) shapes.push("parallel");
  else {
    // point nearest to every line in the least-squares sense: Σ (I − d dᵀ)(X − P) = 0
    const projector = (d) => [0, 1, 2].map((i) => [0, 1, 2].map((j) => (i === j ? 1 : 0) - d[i] * d[j]));
    const projectors = directions.map(projector);
    const matrix = [0, 1, 2].map((i) => [0, 1, 2].map((j) => projectors.reduce((s, p) => s + p[i][j], 0)));
    const apply = (p, v) => [0, 1, 2].map((i) => p[i][0] * v[0] + p[i][1] * v[1] + p[i][2] * v[2]);
    const rhs = projectors.reduce((s, p, i) => add(s, apply(p, points[i])), [0, 0, 0]);
    const meet = solve3(matrix, rhs);
    const worst = Math.max(...projectors.map((p, i) => norm(apply(p, sub(meet, points[i])))));
    if (worst <= EPS * L) shapes.push("concurrent");
  }
  // every point P_i and P_i + L·d_i in the plane of the two spokes with the largest cross product
  const cloud = [...points, ...points.map((p, i) => add(p, scale(directions[i], L)))];
  const spokes = cloud.slice(1).map((p) => sub(p, cloud[0]));
  let best = -1;
  let bestCross = null;
  for (const a of spokes) {
    for (const b of spokes) {
      const c = cross(a, b);
      const size = norm(c);
      if (size > best) (best = size), (bestCross = c);
    }
  }
  if (best <= EPS * L * L) shapes.push("coplanar");
  else {
    const normal = scale(bestCross, 1 / best);
    if (Math.max(...spokes.map((s) => Math.abs(dot(s, normal)))) <= EPS * L) shapes.push("coplanar");
  }
  return shapes;
}

export function checkSystem(system) {
  if (!system.forces.length) throw new InputError("noForces");
  const values = [...system.forces.flat(), ...system.points.flat(), ...system.Q, ...system.A, ...system.u];
  if (!values.every(Number.isFinite)) throw new InputError("notFinite");
  if (norm(system.u) === 0) throw new InputError("zeroU");
}

// Items a) to g) of the statement.
export function reduce(system) {
  checkSystem(system);
  let R = [0, 0, 0];
  for (const f of system.forces) R = add(R, f);
  const MQ = momentAbout(system, system.Q);
  const MA = add(MQ, cross(sub(system.Q, system.A), R)); // transport of moments
  const unitU = scale(system.u, 1 / norm(system.u));
  const I = dot(R, MQ);
  const S = system.forces.reduce((s, f) => s + norm(f), 0);
  const L = lengthScale(system);
  const category = classify(R, MQ, I, S, L);
  let axisPoint = null;
  let axisDirection = null;
  let ME = null;
  if (category === SINGLE_FORCE || category === FORCE_COUPLE) {
    const r2 = dot(R, R);
    axisPoint = add(system.Q, scale(cross(R, MQ), 1 / r2));
    axisDirection = scale(R, 1 / Math.sqrt(r2));
    ME = scale(R, I / r2);
  }
  return {
    R, MQ, MA, unitU, axisTorque: dot(MA, unitU), I, category,
    shape: forceShape(system, S, L), axisPoint, axisDirection, ME, forceScale: S, lengthScale: L,
  };
}

// Rodrigues rotation of v by theta about the unit vector u (used by the 3D view, not by the reduction).
export function rotate(v, u, theta) {
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  return add(add(scale(v, c), scale(cross(u, v), s)), scale(u, dot(u, v) * (1 - c)));
}

// Small seeded generator (mulberry32), so a verification run can be repeated.
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
