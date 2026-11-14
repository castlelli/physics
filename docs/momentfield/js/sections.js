// The two sections that prove the axisymmetry. Both are data filters over the lab's field:
// only the poles of the chosen plane are drawn, then the camera is aimed at that plane.

import { add, axialSection, cross, dot, moment, norm, rotate, scale, sub } from "./model.js";
import { fieldContent } from "./field.js";
import { createScene } from "./scene.js";
import { Plot, fmt, fmtSci, onResize, onThemeChange, reducedMotion, theme, trimmed } from "./ui.js";
import { T } from "./i18n.js";

// ---------------------------------------------------------------- normal section

export function createNormalSection(lab) {
  const root = document.getElementById("corte-normal");
  const main = createScene(document.getElementById("normal-scene"), { interactive: false, gizmo: true });
  const side = createScene(document.getElementById("normal-side"), { interactive: false, gizmo: true });
  const slider = root.querySelector("#normal-s");
  const label = root.querySelector("[data-normal-s]");
  const turnButton = root.querySelector("[data-normal-turn]");
  const note = root.querySelector("[data-normal-note]");
  let field = null;
  let s = 0;
  let turn = 0; // current animation angle, radians
  let animating = false;

  // Poles of one plane at axial offset s, with the lab's rays and radii.
  function plane(offset) {
    const { u, v1, v2 } = field.basis;
    const cfg = field.config;
    const P = field.forcePoint;
    const foot = add(P, scale(u, offset));
    const poles = [];
    for (let j = 0; j < cfg.nRays; j++) {
      const theta = (j * cfg.angleStepDeg * Math.PI) / 180;
      for (let k = 0; k < cfg.nRadii; k++) {
        const r = (k + 1) * cfg.radiusStep;
        const pole = add(foot, add(scale(v1, r * Math.cos(theta)), scale(v2, r * Math.sin(theta))));
        poles.push({ pole, foot, moment: moment(pole, P, field.force) });
      }
    }
    return { foot, poles };
  }

  function content(colors) {
    const { u } = field.basis;
    const k = lab.scales().moment;
    const show = lab.show();
    const { foot, poles } = plane(s);
    const items = [];
    const bounds = [];
    const maxRadius = field.config.nRadii * field.config.radiusStep;
    // faint rings at each radius: the moments are tangent to them
    for (let i = 1; i <= field.config.nRadii; i++) {
      const r = i * field.config.radiusStep;
      const { v1, v2 } = field.basis;
      for (let a = 0; a < 72; a++) {
        const t0 = (a / 72) * 2 * Math.PI;
        const t1 = ((a + 1) / 72) * 2 * Math.PI;
        items.push({
          kind: "segment",
          a: add(foot, add(scale(v1, r * Math.cos(t0)), scale(v2, r * Math.sin(t0)))),
          b: add(foot, add(scale(v1, r * Math.cos(t1)), scale(v2, r * Math.sin(t1)))),
          color: colors.line,
          width: 1,
        });
      }
    }
    const ghost = turn !== 0;
    for (const p of poles) {
      const tip = add(p.pole, scale(p.moment, k));
      if (ghost) {
        items.push({ kind: "arrow", a: p.pole, b: tip, color: colors.ink3, width: 1.4, head: 9, alpha: 0.35 });
      }
      // the drawing turned rigidly by `turn` about the axis
      const pole = add(foot, rotate(sub(p.pole, foot), u, turn));
      const drawnTip = add(foot, rotate(sub(tip, foot), u, turn));
      if (show.poleFoot) items.push({ kind: "segment", a: pole, b: foot, color: colors.poleFoot, width: 1.3, dash: [6, 5] });
      if (show.tipFoot) items.push({ kind: "segment", a: drawnTip, b: foot, color: colors.tipFoot, width: 1.3, dash: [6, 5] });
      items.push({ kind: "arrow", a: pole, b: drawnTip, color: colors.ink, width: 2, head: 10 });
      items.push({ kind: "dot", p: pole, color: colors.ink, radius: 2.8 });
      bounds.push(p.pole, tip);
    }
    items.push({ kind: "glyph", p: foot, outward: true, radius: 9, color: colors.force, width: 2, lift: 1 });
    // square bounds around the foot, independent of s, so the picture really does not move
    const { v1, v2 } = field.basis;
    const reach = Math.max(maxRadius, ...bounds.map((b) => norm(sub(b, foot)))) * 1.08;
    for (const e of [v1, v2]) bounds.push(add(foot, scale(e, reach)), sub(foot, scale(e, reach)));
    return { items, bounds, pickables: [] };
  }

  function sideContent(colors) {
    const options = { ...drawOptions(), samples: field.samples, selected: null };
    const base = fieldContent(field, colors, options);
    for (const item of base.items) {
      if (item.color !== colors.force) item.alpha = (item.alpha ?? 1) * 0.16;
    }
    const k = lab.scales().moment;
    const { foot, poles } = plane(s);
    const { v1 } = field.basis;
    const reach = field.config.nRadii * field.config.radiusStep * 1.25;
    base.items.push({ kind: "segment", a: add(foot, scale(v1, reach)), b: sub(foot, scale(v1, reach)), color: colors.ink3, width: 1.2, dash: [3, 4] });
    for (const p of poles) {
      base.items.push({ kind: "arrow", a: p.pole, b: add(p.pole, scale(p.moment, k)), color: colors.ink, width: 2, head: 10, lift: 0.3 });
      base.items.push({ kind: "dot", p: p.pole, color: colors.ink, radius: 2.8, lift: 0.3 });
    }
    return base;
  }

  function drawOptions() {
    const show = lab.show();
    return { momentScale: lab.scales().moment, forceScale: lab.scales().force, poleFoot: show.poleFoot, tipFoot: show.tipFoot };
  }

  function sRange() {
    const offsets = field.planeOffsets;
    const reach = Math.max(...offsets.map(Math.abs)) + field.config.planeSpacing;
    return [-reach, reach];
  }

  function render() {
    if (!field) return;
    const [lo, hi] = sRange();
    s = Math.min(hi, Math.max(lo, s));
    slider.min = String(lo);
    slider.max = String(hi);
    slider.value = String(s);
    slider.style.setProperty("--fill", `${((s - lo) / (hi - lo)) * 100}%`);
    label.textContent = `s = ${fmt(s, 2)}`;
    main.setContent(content);
    side.setContent(sideContent);
  }

  function setField(next, message) {
    field = next;
    if (!field) {
      main.setMessage(message);
      side.setMessage(message);
      turnButton.disabled = true;
      note.textContent = "";
      return;
    }
    turnButton.disabled = false;
    turnButton.textContent = T.turnButton(trimmed(field.config.angleStepDeg, 0));
    const { u, v1, v2 } = field.basis;
    main.setFrame({ right: v1, up: v2 }); // back = v1 ∧ v2 = u: F points at the reader
    side.setFrame({ right: u, up: v1 }); // back = u ∧ v1 = v2: the plane is seen edge-on
    if (!animating) note.textContent = T.normalNote;
    render();
  }

  // Turn the drawing by one angle step and measure how far it lands from the original.
  function deviation() {
    const { u } = field.basis;
    const step = (field.config.angleStepDeg * Math.PI) / 180;
    const { foot, poles } = plane(s);
    let worst = 0;
    let biggest = 0;
    for (const p of poles) biggest = Math.max(biggest, norm(p.moment));
    for (const p of poles) {
      const turnedPole = add(foot, rotate(sub(p.pole, foot), u, step));
      const turnedMoment = rotate(p.moment, u, step);
      let match = null;
      let best = Infinity;
      for (const q of poles) {
        const d = norm(sub(q.pole, turnedPole));
        if (d < best) (best = d), (match = q);
      }
      worst = Math.max(worst, norm(sub(match.moment, turnedMoment)) / biggest, best / (field.config.nRadii * field.config.radiusStep));
    }
    return worst;
  }

  turnButton.addEventListener("click", () => {
    if (!field || animating) return;
    const step = (field.config.angleStepDeg * Math.PI) / 180;
    const duration = reducedMotion() ? 0 : 1100;
    const start = performance.now();
    animating = true;
    note.textContent = T.turning;
    const tick = (time) => {
      const f = duration ? Math.min(1, (time - start) / duration) : 1;
      turn = step * (f < 0.5 ? 4 * f * f * f : 1 - (-2 * f + 2) ** 3 / 2);
      main.setContent(content, { keepFit: true });
      if (f < 1) return requestAnimationFrame(tick);
      animating = false;
      turn = 0;
      main.setContent(content, { keepFit: true });
      note.textContent = T.turned(trimmed(field.config.angleStepDeg, 0), fmtSci(deviation(), 1));
    };
    requestAnimationFrame(tick);
  });

  slider.addEventListener("input", () => {
    s = Number(slider.value);
    render();
  });

  lab.onChange(setField);
}

// ---------------------------------------------------------------- axial section

export function createAxialSection(lab) {
  const root = document.getElementById("corte-axial");
  const scene = createScene(document.getElementById("axial-scene"), { interactive: false });
  const caption = root.querySelector("[data-axial-caption]");
  const note = root.querySelector("[data-axial-note]");
  const viewButtons = [...root.querySelectorAll("[data-axial-view] button")];
  const plotCanvas = document.getElementById("axial-plot");
  const plot = new Plot(plotCanvas, { xLabel: T.plotX, yLabel: "M · n", margin: { left: 52, right: 14, top: 12, bottom: 34 } });
  let field = null;
  let view = "front";

  function geometry() {
    const { u, v1 } = field.basis;
    const n = cross(v1, u); // normal to the page when v1 is to the right and u is up
    const samples = axialSection(field);
    return { u, v1, n, samples };
  }

  function content(colors) {
    const { u, v1, n, samples } = geometry();
    const show = lab.show();
    if (view === "tilted") {
      return fieldContent(field, colors, {
        momentScale: lab.scales().moment,
        forceScale: lab.scales().force,
        poleFoot: show.poleFoot,
        tipFoot: show.tipFoot,
        samples,
      });
    }
    const P = field.forcePoint;
    let reach = 0;
    for (const s of field.samples) reach = Math.max(reach, Math.abs(s.axialOffset) + s.radialDistance);
    const half = 1.3 * reach + 0.5;
    const items = [
      { kind: "segment", a: sub(P, scale(u, half)), b: add(P, scale(u, half)), color: colors.force, width: 1.6 },
      { kind: "arrow", a: P, b: add(P, scale(field.force, lab.scales().force)), color: colors.force, width: 3.2, head: 15 },
      { kind: "text", p: add(P, scale(field.force, lab.scales().force)), text: "F", color: colors.force, offset: [10, -6], size: 15 },
    ];
    const bounds = [P];
    const biggest = Math.max(...samples.map((s) => norm(s.moment)), 1e-300);
    for (const s of samples) {
      if (show.poleFoot) items.push({ kind: "segment", a: s.pole, b: s.foot, color: colors.poleFoot, width: 1.3, dash: [6, 5] });
      const m = dot(s.moment, n);
      items.push({ kind: "glyph", p: s.pole, outward: m > 0, radius: 4 + 14 * (Math.abs(m) / biggest), color: colors.ink, width: 1.8 });
      bounds.push(s.pole, s.foot);
    }
    for (const b of [...bounds]) bounds.push(add(b, scale(v1, 0.6)), sub(b, scale(v1, 0.6)));
    return { items, bounds, pickables: [] };
  }

  function drawPlot() {
    if (!field) return;
    const { v1, n, samples } = geometry();
    const colors = theme();
    const normF = norm(field.force);
    const points = samples.map((s) => ({ x: dot(sub(s.pole, field.forcePoint), v1), y: dot(s.moment, n), plane: s.plane }));
    const xMax = Math.max(...points.map((p) => Math.abs(p.x))) * 1.2 || 1;
    const yMax = normF * xMax;
    plot.setView(-xMax, xMax, -yMax * 1.1, yMax * 1.1);
    const ctx = plot.begin();
    plot.zeroLines();
    plot.clip(() => {
      ctx.strokeStyle = colors.ink3;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(plot.px(-xMax), plot.py(normF * xMax));
      ctx.lineTo(plot.px(xMax), plot.py(-normF * xMax));
      ctx.stroke();
      ctx.lineWidth = 1.6;
      for (const p of points) {
        // concentric rings: one per plane, all on top of each other
        ctx.strokeStyle = colors.ink;
        ctx.beginPath();
        ctx.arc(plot.px(p.x), plot.py(p.y), 4 + 2.2 * p.plane, 0, 2 * Math.PI);
        ctx.stroke();
      }
    });
    ctx.fillStyle = colors.ink2;
    ctx.font = `14px ${colors.sans}`;
    // the line runs from upper left to lower right, so the lower-left quadrant is free for its label
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    const { left, top, height } = plot.inner;
    ctx.fillText(T.plotLine, left + 8, top + height - 26);
    ctx.fillText(`|F| = ${fmt(normF, 3)}`, left + 8, top + height - 8);
  }

  function lineError() {
    const { v1, n, samples } = geometry();
    const normF = norm(field.force);
    let worst = 0;
    let biggest = 0;
    for (const s of samples) {
      const d = dot(sub(s.pole, field.forcePoint), v1);
      const m = dot(s.moment, n);
      const inPlane = sub(s.moment, scale(n, m));
      biggest = Math.max(biggest, norm(s.moment));
      worst = Math.max(worst, Math.abs(m + normF * d), norm(inPlane));
    }
    return worst / (biggest || 1);
  }

  function setView(next) {
    view = next;
    for (const button of viewButtons) button.setAttribute("aria-pressed", String(button.dataset.view === view));
    if (!field) return;
    const { u, v1 } = field.basis;
    if (view === "front") {
      scene.setFrame({ right: v1, up: u });
      caption.textContent = T.axialFront;
    } else {
      // camera 20° above the normal of the plane: the out-of-page arrows show
      const tilt = (20 * Math.PI) / 180;
      scene.setFrame({ right: v1, up: rotate(u, v1, -tilt) });
      caption.textContent = T.axialTilted;
    }
    scene.setContent(content);
  }

  function setField(next, message) {
    field = next;
    if (!field) {
      scene.setMessage(message);
      note.textContent = "";
      plot.begin();
      return;
    }
    setView(view);
    drawPlot();
    const oneSide = field.config.nRays % 2 === 1;
    note.textContent =
      (oneSide ? T.oneSide(trimmed(field.config.angleStepDeg, 0)) : "") + T.axialNote(fmtSci(lineError(), 1));
  }

  for (const button of viewButtons) button.addEventListener("click", () => setView(button.dataset.view));
  onResize(plotCanvas, drawPlot);
  onThemeChange(drawPlot);
  lab.onChange(setField);
}
