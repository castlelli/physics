// Scene content for figures 1 and 2 of the statement. Forces have one arrowhead, moments two.
// Colours: forces in ink, R orange, M_Q blue, M_A violet, axis Au grey, central axis and M_E green.

import { add, dot, norm, scale, sub } from "./model.js";

// Largest drawn force and largest drawn moment both at 40 % of the box diagonal (as figuras.auto_scale).
export function drawScales(system, r) {
  const diagonal = norm(system.box);
  const forces = Math.max(...system.forces.map(norm), norm(r.R));
  const moments = Math.max(norm(r.MQ), norm(r.MA), r.ME ? norm(r.ME) : 0);
  return { force: forces > 0 ? (0.4 * diagonal) / forces : 1, moment: moments > 0 ? (0.4 * diagonal) / moments : 1 };
}

function boxItems(box, colors, items, bounds) {
  const [a, b, c] = box;
  const v = [];
  for (const x of [0, a]) for (const y of [0, b]) for (const z of [0, c]) v.push([x, y, z]);
  for (let i = 0; i < 8; i++) {
    for (let j = i + 1; j < 8; j++) {
      const differ = [0, 1, 2].filter((k) => v[i][k] !== v[j][k]).length;
      if (differ === 1) items.push({ kind: "segment", a: v[i], b: v[j], color: colors.box, width: 1.2, split: 4 });
    }
  }
  bounds.push(...v);
}

function frameItems(box, colors, items) {
  const length = 0.45 * Math.min(...box) + 0.3;
  ["x", "y", "z"].forEach((name, k) => {
    const e = [0, 0, 0];
    e[k] = length;
    items.push({ kind: "arrow", a: [0, 0, 0], b: e, color: colors.ink3, width: 1.3, head: 8 });
    items.push({ kind: "text", p: scale(e, 1.15), text: name, color: colors.ink3, size: 13, offset: [-4, 0] });
  });
  items.push({ kind: "text", p: [0, 0, 0], text: "O", color: colors.ink3, size: 13, offset: [-16, -10] });
}

function forceItems(system, colors, k, items, bounds) {
  system.forces.forEach((f, i) => {
    const P = system.points[i];
    const tip = add(P, scale(f, k));
    items.push({ kind: "dot", p: P, color: colors.ink, radius: 3 });
    items.push({ kind: "text", p: P, text: `P${sub_(i + 1)}`, color: colors.ink2, size: 13, offset: [-22, 12] });
    if (norm(f) > 0) {
      items.push({ kind: "arrow", a: P, b: tip, color: colors.ink, width: 2.2, head: 11 });
      items.push({ kind: "text", p: tip, text: `F${sub_(i + 1)}`, color: colors.ink, size: 14, offset: [6, -8] });
    }
    bounds.push(P, tip);
  });
}

const SUBSCRIPTS = "₀₁₂₃₄₅₆₇₈₉";
function sub_(n) {
  return String(n).replace(/\d/g, (d) => SUBSCRIPTS[d]);
}

function vectorItem(items, bounds, from, vector, color, label, { double = false, width = 2.4 } = {}) {
  if (norm(vector) === 0) return;
  const tip = add(from, vector);
  items.push({ kind: "arrow", a: from, b: tip, color, width, head: 12, double, lift: 0.02 });
  items.push({ kind: "text", p: tip, text: label, color, size: 14, offset: [8, -8], lift: 0.02 });
  bounds.push(tip);
}

function pointItem(items, bounds, p, label, color) {
  items.push({ kind: "dot", p, color, radius: 4, lift: 0.03 });
  items.push({ kind: "text", p, text: label, color, size: 14, offset: [8, 14], lift: 0.03 });
  bounds.push(p);
}

// Item h: Oxyz, F_i at P_i, Q, the axis Au, R and M_Q at Q, M_A at A.
export function figureOne(system, r, colors, scales) {
  const items = [];
  const bounds = [];
  boxItems(system.box, colors, items, bounds);
  frameItems(system.box, colors, items);
  forceItems(system, colors, scales.force, items, bounds);
  const diagonal = norm(system.box);
  const reach = scale(r.unitU, 0.6 * diagonal);
  items.push({ kind: "segment", a: sub(system.A, reach), b: add(system.A, reach), color: colors.axisU, width: 1.5, dash: [10, 4, 2, 4], split: 12 });
  items.push({ kind: "text", p: add(system.A, scale(reach, 0.7)), text: "Au", color: colors.axisU, size: 13, offset: [8, -10] });
  pointItem(items, bounds, system.Q, "Q", colors.momentQ);
  pointItem(items, bounds, system.A, "A", colors.momentA);
  vectorItem(items, bounds, system.Q, scale(r.R, scales.force), colors.resultant, "R", { width: 3 });
  vectorItem(items, bounds, system.Q, scale(r.MQ, scales.moment), colors.momentQ, "M_Q", { double: true });
  vectorItem(items, bounds, system.A, scale(r.MA, scales.moment), colors.momentA, "M_A", { double: true });
  return { items, bounds, pickables: [] };
}

// Point of the central axis nearest the centre of the box: R and M_E are drawn there, so they sit on
// the body whenever the axis crosses it (same as figuras.axis_anchor).
export function axisAnchor(system, r) {
  const centre = scale(system.box, 0.5);
  return add(r.axisPoint, scale(r.axisDirection, dot(sub(centre, r.axisPoint), r.axisDirection)));
}

// Item i: Oxyz, F_i at P_i, Q and M_Q, the central axis with R and M_E on it.
export function figureTwo(system, r, colors, scales) {
  const items = [];
  const bounds = [];
  boxItems(system.box, colors, items, bounds);
  frameItems(system.box, colors, items);
  forceItems(system, colors, scales.force, items, bounds);
  pointItem(items, bounds, system.Q, "Q", colors.momentQ);
  vectorItem(items, bounds, system.Q, scale(r.MQ, scales.moment), colors.momentQ, "M_Q", { double: true });
  if (r.axisPoint) {
    const diagonal = norm(system.box);
    const anchor = axisAnchor(system, r);
    const reach = scale(r.axisDirection, 0.8 * diagonal);
    items.push({ kind: "segment", a: sub(anchor, reach), b: add(anchor, reach), color: colors.central, width: 2, split: 16 });
    pointItem(items, bounds, r.axisPoint, "E", colors.central);
    vectorItem(items, bounds, anchor, scale(r.R, scales.force), colors.resultant, "R", { width: 3 });
    vectorItem(items, bounds, anchor, scale(r.ME, scales.moment), colors.central, "M_E", { double: true });
  }
  return { items, bounds, pickables: [] };
}
