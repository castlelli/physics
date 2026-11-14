// Laboratory: P, F and the sampling as inputs; the 3D field, pole picking and the O–Q–tip readout.
// Other sections subscribe with onChange and redraw from the same sampled field.

import { InputError, autoScale, dot, norm, sampleField } from "./model.js";
import { angleAtPole, fieldContent } from "./field.js";
import { createScene, frameForAxis } from "./scene.js";
import { fmt, fmtSci, theme, trimmed, watchVisibility } from "./ui.js";
import { T } from "./i18n.js";

const C = T.controls;
const CONTROLS = [
  { group: T.groups.force, key: "Fx", symbol: "F<sub>x</sub>", name: C.Fx, min: -5, max: 5, step: 0.1 },
  { group: T.groups.force, key: "Fy", symbol: "F<sub>y</sub>", name: C.Fy, min: -5, max: 5, step: 0.1 },
  { group: T.groups.force, key: "Fz", symbol: "F<sub>z</sub>", name: C.Fz, min: -5, max: 5, step: 0.1 },
  { group: T.groups.point, key: "Px", symbol: "P<sub>x</sub>", name: C.Px, min: -5, max: 5, step: 0.1 },
  { group: T.groups.point, key: "Py", symbol: "P<sub>y</sub>", name: C.Py, min: -5, max: 5, step: 0.1 },
  { group: T.groups.point, key: "Pz", symbol: "P<sub>z</sub>", name: C.Pz, min: -5, max: 5, step: 0.1 },
  { group: T.groups.poles, key: "nPlanes", symbol: C.nPlanes[0], name: C.nPlanes[1], min: 1, max: 7, step: 1 },
  { group: T.groups.poles, key: "planeSpacing", symbol: C.planeSpacing[0], name: C.planeSpacing[1], min: 0.25, max: 3, step: 0.05 },
  { group: T.groups.poles, key: "nRadii", symbol: C.nRadii[0], name: C.nRadii[1], min: 1, max: 4, step: 1 },
  { group: T.groups.poles, key: "radiusStep", symbol: C.radiusStep[0], name: C.radiusStep[1], min: 0.25, max: 2, step: 0.05 },
  { group: T.groups.drawing, key: "momentFactor", symbol: C.momentFactor[0], name: C.momentFactor[1], min: 0.25, max: 4, step: 0.01, log: true, unit: "× auto" },
];
const STEPS = [30, 45, 60, 90, 120];

export function createLab(report) {
  const root = document.getElementById("lab");
  const nodes = {
    cases: root.querySelector("[data-case-bar]"),
    controls: root.querySelector("[data-controls]"),
    steps: root.querySelector("[data-step]"),
    spin: root.querySelector("[data-spin]"),
    home: root.querySelector("[data-home]"),
    status: root.querySelector("[data-status]"),
    scaleLabel: root.querySelector("[data-scale-label]"),
    pole: Object.fromEntries([...root.querySelectorAll("[data-pole-out]")].map((n) => [n.dataset.poleOut, n])),
  };

  const state = {
    Fx: 2, Fy: 1, Fz: -1.5, Px: 1, Py: 0, Pz: 2,
    nPlanes: 3, planeSpacing: 1.5, angleStepDeg: 60, nRadii: 2, radiusStep: 1,
    momentFactor: 1,
    show: { poleFoot: true, tipFoot: true },
    selected: null,
    caseKey: "relatorio",
  };
  let field = null;
  let scales = { moment: 1, force: 1 };
  let prevV1 = null;
  let previousCounts = "";
  const listeners = [];
  const inputs = {};

  const scene = createScene(document.getElementById("lab-scene"), { onPick: select });

  // ---------------------------------------------------------------- field

  function recompute() {
    const force = [state.Fx, state.Fy, state.Fz];
    const point = [state.Px, state.Py, state.Pz];
    const config = { nPlanes: state.nPlanes, planeSpacing: state.planeSpacing, angleStepDeg: state.angleStepDeg, nRadii: state.nRadii, radiusStep: state.radiusStep };
    try {
      field = sampleField(config, point, force, prevV1);
      prevV1 = field.basis.v1;
    } catch (error) {
      if (!(error instanceof InputError)) throw error;
      field = null;
      prevV1 = null;
      const message = T.errors[error.message] ?? error.message;
      nodes.status.textContent = message;
      scene.setMessage(message);
      showPole();
      listeners.forEach((listener) => listener(null, message));
      return;
    }
    const auto = autoScale(field);
    scales = { moment: auto.moment * state.momentFactor, force: auto.force };
    const counts = `${config.nPlanes}/${field.config.nRays}/${config.nRadii}`;
    if (counts !== previousCounts) state.selected = null;
    // the view re-fits to the new field; the camera keeps the rotation the reader gave it
    scene.setContent((colors) => fieldContent(field, colors, drawOptions()));
    previousCounts = counts;
    nodes.scaleLabel.textContent = trimmed(scales.moment, 3);
    nodes.status.textContent = T.status(field.samples.length, config.nPlanes, field.config.nRays, config.nRadii);
    showPole();
    listeners.forEach((listener) => listener(field, null));
  }

  function drawOptions() {
    return { momentScale: scales.moment, forceScale: scales.force, poleFoot: state.show.poleFoot, tipFoot: state.show.tipFoot, selected: state.selected };
  }

  function select(index) {
    state.selected = index === state.selected ? null : index;
    scene.rebuild();
    showPole();
  }

  function showPole() {
    const s = field && state.selected !== null ? field.samples[state.selected] : null;
    const out = nodes.pole;
    if (!s) {
      out.O.textContent = field ? T.pickPole : "–";
      for (const key of ["Q", "d", "M", "Fd", "Mu", "angle"]) out[key].textContent = "–";
      return;
    }
    const vec = (v) => `(${v.map((c) => fmt(c, 2)).join(T.vectorSeparator)})`;
    const m = norm(s.moment);
    out.O.textContent = vec(s.pole);
    out.Q.textContent = vec(s.foot);
    out.d.textContent = fmt(s.radialDistance, 3);
    out.M.textContent = fmt(m, 4);
    out.Fd.textContent = fmt(norm(field.force) * s.radialDistance, 4);
    const along = dot(s.moment, field.basis.u);
    out.Mu.textContent = Math.abs(along) < 1e-300 ? "0" : fmtSci(along, 1);
    out.angle.textContent = `${fmt(angleAtPole(s), 4)}°`;
  }

  // ---------------------------------------------------------------- inputs

  function buildControls() {
    let group = null;
    let box = null;
    for (const control of CONTROLS) {
      if (control.group !== group) {
        group = control.group;
        box = document.createElement("fieldset");
        box.className = "control-group";
        box.innerHTML = `<legend>${group}</legend>`;
        nodes.controls.appendChild(box);
      }
      const row = document.createElement("div");
      row.className = "control";
      const id = `ctl-${control.key}`;
      row.innerHTML = `
        <label for="${id}"><span class="symbol">${control.symbol}</span><span class="name">${control.name}</span></label>
        <span class="field"><input id="${id}" type="number" inputmode="decimal" step="${control.step}" min="${control.min}" max="${control.max}"><span class="unit">${control.unit ?? ""}</span></span>
        <input type="range" min="0" max="1000" step="1" aria-label="${control.symbol.replace(/<[^>]+>/g, "")} ${control.name}">`;
      box.appendChild(row);
      const number = row.querySelector('input[type="number"]');
      const slider = row.querySelector('input[type="range"]');
      inputs[control.key] = { number, slider, control };
      slider.addEventListener("input", () => {
        const f = Number(slider.value) / 1000;
        const raw = control.log ? control.min * (control.max / control.min) ** f : control.min + f * (control.max - control.min);
        apply(control.key, Math.round(raw / control.step) * control.step);
      });
      number.addEventListener("change", () => {
        const value = Number(number.value.replace(",", "."));
        if (Number.isFinite(value)) apply(control.key, value);
        syncInputs();
      });
    }

    for (const step of STEPS) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${step}°`;
      button.dataset.step = String(step);
      button.addEventListener("click", () => {
        state.angleStepDeg = step;
        state.caseKey = matchingCase();
        syncInputs();
        recompute();
      });
      nodes.steps.appendChild(button);
    }

    for (const box of root.querySelectorAll("[data-show]")) {
      box.addEventListener("change", () => {
        state.show[box.dataset.show] = box.checked;
        scene.rebuild();
        listeners.forEach((listener) => listener(field, null));
      });
    }
  }

  function apply(key, value) {
    const control = CONTROLS.find((c) => c.key === key);
    let v = Math.min(control.max, Math.max(control.min, value));
    if (control.step === 1) v = Math.round(v);
    state[key] = Number(v.toFixed(6));
    state.caseKey = matchingCase();
    syncInputs();
    recompute();
  }

  function syncInputs() {
    for (const [key, { number, slider, control }] of Object.entries(inputs)) {
      const value = state[key];
      if (document.activeElement !== number) number.value = String(Number(value.toFixed(4)));
      const f = control.log ? Math.log(value / control.min) / Math.log(control.max / control.min) : (value - control.min) / (control.max - control.min);
      slider.value = String(Math.round(Math.min(1, Math.max(0, f)) * 1000));
      slider.style.setProperty("--fill", `${Math.min(1, Math.max(0, f)) * 100}%`);
    }
    for (const button of nodes.steps.children) button.setAttribute("aria-pressed", String(Number(button.dataset.step) === state.angleStepDeg));
    for (const chip of nodes.cases.children) chip.setAttribute("aria-pressed", String((chip.dataset.case || null) === (state.caseKey || null)));
  }

  // ---------------------------------------------------------------- cases

  function caseState(item) {
    const c = item.config;
    return {
      Fx: item.force[0], Fy: item.force[1], Fz: item.force[2],
      Px: item.force_point[0], Py: item.force_point[1], Pz: item.force_point[2],
      nPlanes: c.n_planes, planeSpacing: c.plane_spacing, angleStepDeg: c.angle_step_deg, nRadii: c.n_radii, radiusStep: c.radius_step,
    };
  }

  function matchingCase() {
    for (const [key, item] of Object.entries(report.cases)) {
      const target = caseState(item);
      if (Object.entries(target).every(([name, value]) => Math.abs(state[name] - value) < 1e-9)) return key;
    }
    return null;
  }

  function buildCases() {
    const marks = { relatorio: "1", campo1: "2" };
    for (const key of Object.keys(report.cases)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "case-chip";
      button.dataset.case = key;
      button.innerHTML = `<span class="case-letter">${marks[key] ?? "•"}</span><span class="case-title">${T.cases[key] ?? key}</span>`;
      button.addEventListener("click", () => load(key));
      nodes.cases.appendChild(button);
    }
    const free = document.createElement("button");
    free.type = "button";
    free.className = "case-chip";
    free.dataset.case = "";
    free.innerHTML = `<span class="case-letter">∗</span><span class="case-title">${T.cases.free}</span>`;
    free.addEventListener("click", () => {
      state.caseKey = null;
      syncInputs();
      nodes.controls.querySelector("input")?.focus();
    });
    nodes.cases.appendChild(free);
  }

  function load(key) {
    Object.assign(state, caseState(report.cases[key]));
    state.caseKey = key;
    state.selected = null;
    prevV1 = null;
    syncInputs();
    recompute();
    if (field) scene.setFrame(frameForAxis(field.basis.u));
  }

  // ---------------------------------------------------------------- spin

  const spin = { on: false, visible: true, last: 0 };
  function frame(time) {
    if (!spin.on || !spin.visible) return;
    const dt = spin.last ? Math.min(0.05, (time - spin.last) / 1000) : 0;
    spin.last = time;
    scene.spinAboutZ(dt * 0.45);
    requestAnimationFrame(frame);
  }
  function setSpin(on) {
    spin.on = on;
    spin.last = 0;
    nodes.spin.textContent = on ? T.stop : T.spin;
    if (on) requestAnimationFrame(frame);
  }
  scene.setSpin({ pause: () => setSpin(false) });
  nodes.spin.addEventListener("click", () => setSpin(!spin.on));
  nodes.home.addEventListener("click", () => scene.reset());
  watchVisibility(document.getElementById("lab-scene"), (visible) => {
    spin.visible = visible;
    if (visible && spin.on) {
      spin.last = 0;
      requestAnimationFrame(frame);
    }
  });

  buildControls();
  buildCases();
  load("relatorio");

  return {
    onChange(listener) {
      listeners.push(listener);
      listener(field, field ? null : nodes.status.textContent);
    },
    field: () => field,
    scales: () => scales,
    show: () => state.show,
    data: () => ({ forcePoint: [state.Px, state.Py, state.Pz], force: [state.Fx, state.Fy, state.Fz] }),
    colors: theme,
  };
}
