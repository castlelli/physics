// Figure 2 (the central axis with R and M_E) and the plot that shows why that axis is special:
// along a line crossing it at right angles, |M(P)| = √(|M_E|² + |R|² d²) and R · M(P) = I.

import { add, cross, dot, momentAbout, norm, scale } from "./model.js";
import { drawScales, figureTwo } from "./draw.js";
import { createScene, frameFromAngles } from "./scene.js";
import { Plot, fmt, onResize, onThemeChange, theme } from "./ui.js";
import { T } from "./i18n.js";

export function createAxisSection(lab) {
  const root = document.getElementById("eixo");
  const scene = createScene(document.getElementById("axis-scene"));
  const note = root.querySelector("[data-axis-note]");
  lab.onChange((system, r, message) => {
    if (!r) {
      scene.setMessage(message);
      note.textContent = "";
      return;
    }
    const view = lab.caseView();
    if (view) scene.setFrame(frameFromAngles(view[0], view[1]));
    const scales = drawScales(system, r);
    scene.setContent((colors) => figureTwo(system, r, colors, scales));
    note.textContent = r.axisPoint ? T.axisNote[r.category](fmt(norm(r.ME), 3)) : T.noAxisNote[r.category];
  });
}

export function createMinimumSection(lab) {
  const root = document.getElementById("minimo");
  const canvas = document.getElementById("minimum-plot");
  const slider = root.querySelector("#minimum-d");
  const label = root.querySelector("[data-minimum-d]");
  const out = Object.fromEntries([...root.querySelectorAll("[data-minimum-out]")].map((n) => [n.dataset.minimumOut, n]));
  const note = root.querySelector("[data-minimum-note]");
  const plot = new Plot(canvas, { xLabel: T.plotX, yLabel: T.plotY, margin: { left: 52, right: 14, top: 12, bottom: 34 } });
  let state = null;

  // The line of poles: through E (or Q when there is no axis), perpendicular to R.
  function line(system, r) {
    if (r.axisPoint) {
      let w = cross(r.R, r.MQ);
      if (norm(w) < 1e-12 * norm(r.R) * (norm(r.MQ) + 1)) w = cross(r.R, Math.abs(r.R[0]) < 0.9 * norm(r.R) ? [1, 0, 0] : [0, 1, 0]);
      return { origin: r.axisPoint, direction: scale(w, 1 / norm(w)) };
    }
    return { origin: system.Q, direction: [1, 0, 0] };
  }

  function draw() {
    if (!state) return;
    const { system, r, origin, direction, d } = state;
    const colors = theme();
    const span = Math.max(1, 0.8 * norm(system.box));
    const R2 = dot(r.R, r.R);
    const ME2 = r.ME ? dot(r.ME, r.ME) : dot(r.MQ, r.MQ);
    const curve = (t) => Math.sqrt(ME2 + R2 * t * t);
    const top = Math.max(curve(span), 1e-9) * 1.15;
    plot.xLabel = r.axisPoint ? T.plotX : T.plotXNoAxis;
    plot.setView(-span, span, 0, top);
    const ctx = plot.begin();
    plot.clip(() => {
      ctx.strokeStyle = colors.central;
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i <= 200; i++) {
        const t = -span + (2 * span * i) / 200;
        const x = plot.px(t);
        const y = plot.py(curve(t));
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
      // moments summed directly over the forces, at 13 poles on the line
      ctx.strokeStyle = colors.ink;
      ctx.lineWidth = 1.6;
      for (let i = 0; i <= 12; i++) {
        const t = -span + (2 * span * i) / 12;
        const m = norm(momentAbout(system, add(origin, scale(direction, t))));
        ctx.beginPath();
        ctx.arc(plot.px(t), plot.py(m), 4, 0, 2 * Math.PI);
        ctx.stroke();
      }
      const here = momentAbout(system, add(origin, scale(direction, d)));
      ctx.fillStyle = colors.resultant;
      ctx.beginPath();
      ctx.arc(plot.px(d), plot.py(norm(here)), 6, 0, 2 * Math.PI);
      ctx.fill();
      out.M.textContent = fmt(norm(here), 4);
      out.RM.textContent = fmt(Math.abs(dot(r.R, here)) < 5e-13 ? 0 : dot(r.R, here), 4);
    });
    ctx.fillStyle = colors.ink2;
    ctx.font = `14px ${colors.sans}`;
    ctx.textAlign = "right";
    ctx.textBaseline = "top";
    const { left, top: y0, width } = plot.inner;
    ctx.fillText(T.plotCurve, left + width - 8, y0 + 8);
    label.textContent = `d = ${fmt(d, 2)}`;
  }

  lab.onChange((system, r) => {
    if (!r) {
      state = null;
      plot.begin();
      return;
    }
    const { origin, direction } = line(system, r);
    const span = Math.max(1, 0.8 * norm(system.box));
    slider.min = String(-span);
    slider.max = String(span);
    const d = Math.min(span, Math.max(-span, state ? state.d : 0.6 * span));
    slider.value = String(d);
    state = { system, r, origin, direction, d };
    out.I.textContent = fmt(Math.abs(r.I) < 5e-13 ? 0 : r.I, 4);
    out.ME.textContent = r.ME ? fmt(norm(r.ME), 4) : "–";
    note.textContent = r.axisPoint ? T.minimumNote : T.minimumNoteCouple;
    fill();
    draw();
  });

  function fill() {
    const lo = Number(slider.min);
    const hi = Number(slider.max);
    slider.style.setProperty("--fill", `${((Number(slider.value) - lo) / (hi - lo)) * 100}%`);
  }

  slider.addEventListener("input", () => {
    if (!state) return;
    state.d = Number(slider.value);
    fill();
    draw();
  });
  onResize(canvas, draw);
  onThemeChange(draw);
}
