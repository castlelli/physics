// Scene content for a sampled field, with the statement's colours:
// red F and line of action, black (ink) moments, green dashed O → Q, blue dashed drawn tip → Q.

import { add, dot, norm, scale, sub } from "./model.js";

// options: momentScale, forceScale, poleFoot, tipFoot (booleans), selected (index or null),
// samples (subset to draw; defaults to all), dim (alpha of the samples that are not selected).
export function fieldContent(field, colors, options) {
  const { u } = field.basis;
  const P = field.forcePoint;
  const samples = options.samples ?? field.samples;
  const k = options.momentScale;
  const items = [];
  const bounds = [P];
  const pickables = [];

  let reach = 0;
  for (const s of field.samples) reach = Math.max(reach, Math.abs(s.axialOffset) + s.radialDistance);
  const half = 1.35 * reach + 0.5;
  items.push({ kind: "segment", a: sub(P, scale(u, half)), b: add(P, scale(u, half)), color: colors.force, width: 1.6, split: 32 });
  const forceTip = add(P, scale(field.force, options.forceScale));
  items.push({ kind: "arrow", a: P, b: forceTip, color: colors.force, width: 3.2, head: 15, lift: 0.02 });
  items.push({ kind: "dot", p: P, color: colors.force, radius: 3.5, lift: 0.02 });
  items.push({ kind: "text", p: P, text: "P", color: colors.force, offset: [10, 12], size: 15 });
  items.push({ kind: "text", p: forceTip, text: "F", color: colors.force, offset: [10, -10], size: 15 });
  bounds.push(forceTip);

  const selected = options.selected ?? null;
  for (const s of samples) {
    const index = field.samples.indexOf(s);
    const isSelected = index === selected;
    const alpha = selected === null || isSelected ? 1 : options.dim ?? 0.22;
    const tip = add(s.pole, scale(s.moment, k));
    const emphasis = isSelected ? 1 : 0;
    if (options.poleFoot !== false)
      items.push({ kind: "segment", a: s.pole, b: s.foot, color: colors.poleFoot, width: 1.3 + emphasis, dash: [6, 5], alpha });
    if (options.tipFoot !== false)
      items.push({ kind: "segment", a: tip, b: s.foot, color: colors.tipFoot, width: 1.3 + emphasis, dash: [6, 5], alpha });
    items.push({ kind: "arrow", a: s.pole, b: tip, color: colors.ink, width: 2 + emphasis, head: 10 + 2 * emphasis, alpha });
    items.push({ kind: "dot", p: s.pole, color: colors.ink, radius: isSelected ? 4 : 2.8, alpha, ring: isSelected ? colors.ink : null });
    bounds.push(s.pole, tip, s.foot);
    pickables.push({ id: index, p: s.pole });
  }

  if (selected !== null && field.samples[selected]) items.push(...triangleMarks(field.samples[selected], k, colors));
  return { items, bounds, pickables };
}

// Right-angle mark at O and labels O, Q for the selected pole.
function triangleMarks(s, k, colors) {
  const toFoot = sub(s.foot, s.pole);
  const along = norm(toFoot);
  const m = norm(s.moment);
  if (along === 0 || m === 0) return [];
  const a = 0.16 * Math.min(along, k * m);
  const e1 = scale(toFoot, 1 / along);
  const e2 = scale(s.moment, 1 / m);
  const c1 = add(s.pole, scale(e1, a));
  const c3 = add(s.pole, scale(e2, a));
  const c2 = add(c1, scale(e2, a));
  return [
    { kind: "segment", a: c1, b: c2, color: colors.ink, width: 1.4, lift: 0.05 },
    { kind: "segment", a: c2, b: c3, color: colors.ink, width: 1.4, lift: 0.05 },
    { kind: "dot", p: s.foot, color: colors.ink, radius: 3.5, lift: 0.05 },
    { kind: "text", p: s.foot, text: "Q", color: colors.ink, offset: [-16, -12], size: 15, lift: 0.05 },
    { kind: "text", p: s.pole, text: "O", color: colors.ink, offset: [10, 14], size: 15, lift: 0.05 },
  ];
}

// Angle at O between O → Q and M, in degrees (90 by the theory).
export function angleAtPole(s) {
  const toFoot = sub(s.foot, s.pole);
  const cosine = dot(toFoot, s.moment) / (norm(toFoot) * norm(s.moment));
  return (Math.acos(Math.max(-1, Math.min(1, cosine))) * 180) / Math.PI;
}

