// Lab: the statement's inputs (forces, points, Q, A, u, box), figure 1 and the results table.
// Other sections subscribe with onChange and redraw from the same reduction.

import { InputError, boxContains, norm, reduce } from "./model.js";
import { drawScales, figureOne } from "./draw.js";
import { createScene, frameFromAngles } from "./scene.js";
import { fmt, theme, watchVisibility } from "./ui.js";
import { T } from "./i18n.js";

const MAX_FORCES = 8;
const GROUP_ORDER = ["null", "couple", "single_force", "force_couple"];

export function createLab(golden) {
  const root = document.getElementById("lab");
  const nodes = {
    cases: root.querySelector("[data-case-bar]"),
    forces: root.querySelector("[data-forces]"),
    add: root.querySelector("[data-add-force]"),
    vectors: Object.fromEntries([...root.querySelectorAll("[data-vec]")].map((n) => [n.dataset.vec, n])),
    results: root.querySelector("[data-results]"),
    status: root.querySelector("[data-status]"),
    spin: root.querySelector("[data-spin]"),
    home: root.querySelector("[data-home]"),
    scaleForce: root.querySelector("[data-scale-force]"),
    scaleMoment: root.querySelector("[data-scale-moment]"),
  };
  const scene = createScene(document.getElementById("lab-scene"));
  const listeners = [];
  let system = null;
  let reduction = null;
  let caseKey = null;

  const vec = (v) => `(${v.map((c) => fmt(clean(c), 3)).join(T.vectorSeparator)})`;
  const clean = (x) => (Math.abs(x) < 5e-13 ? 0 : x);

  // ---------------------------------------------------------------- reduction and drawing

  function recompute() {
    try {
      reduction = reduce(system);
    } catch (error) {
      if (!(error instanceof InputError)) throw error;
      reduction = null;
      const message = T.errors[error.message] ?? error.message;
      nodes.status.textContent = message;
      scene.setMessage(message);
      nodes.results.innerHTML = "";
      listeners.forEach((listener) => listener(system, null, message));
      return;
    }
    const scales = drawScales(system, reduction);
    nodes.scaleForce.textContent = fmt(scales.force, 3);
    nodes.scaleMoment.textContent = fmt(scales.moment, 3);
    scene.setContent((colors) => figureOne(system, reduction, colors, scales));
    const outside = system.points.filter((p) => !boxContains(system.box, p)).length;
    nodes.status.textContent = T.status(system.forces.length, outside);
    showResults();
    markOutside();
    listeners.forEach((listener) => listener(system, reduction, null));
  }

  function showResults() {
    const r = reduction;
    const rows = [
      [T.rows.R, vec(r.R), fmt(norm(r.R), 3)],
      [T.rows.MQ, vec(r.MQ), fmt(norm(r.MQ), 3)],
      [T.rows.MA, vec(r.MA), fmt(norm(r.MA), 3)],
      [T.rows.torque, fmt(clean(r.axisTorque), 3), `${T.vectorWord} ${vec(r.unitU.map((c) => c * r.axisTorque))}`],
      [T.rows.I, fmt(clean(r.I), 3), ""],
      [T.rows.category, `<b>${T.category[r.category]}</b>`, r.shape.length ? T.forcesAre(r.shape.map((s) => T.shape[s]).join(", ")) : ""],
    ];
    if (r.axisPoint) {
      rows.push([T.rows.axisPoint, vec(r.axisPoint), T.nearestToQ]);
      rows.push([T.rows.axisDirection, vec(r.axisDirection), T.unitR]);
      rows.push([T.rows.ME, vec(r.ME), fmt(norm(r.ME), 3)]);
    } else {
      rows.push([T.rows.noAxis, T.noAxisValue, ""]);
    }
    nodes.results.innerHTML = rows.map(([name, value, note]) => `<tr><th scope="row">${name}</th><td>${value}</td><td>${note}</td></tr>`).join("");
  }

  // ---------------------------------------------------------------- force rows

  function numberInput(value, label, onChange) {
    const input = document.createElement("input");
    input.type = "number";
    input.step = "0.1";
    input.inputMode = "decimal";
    input.value = String(value);
    input.setAttribute("aria-label", label);
    input.addEventListener("input", () => {
      const v = Number(input.value.replace(",", "."));
      if (input.value.trim() !== "" && Number.isFinite(v)) onChange(v);
    });
    return input;
  }

  function buildForceRows() {
    nodes.forces.innerHTML = "";
    system.forces.forEach((force, i) => {
      const row = document.createElement("tr");
      const name = document.createElement("th");
      name.scope = "row";
      name.innerHTML = `F<sub>${i + 1}</sub>`;
      row.appendChild(name);
      const cell = document.createElement("td");
      for (const [vector, letter] of [[force, "F"], [system.points[i], "P"]]) {
        const line = document.createElement("div");
        line.className = `triple ${letter === "P" ? "point" : "force"}`;
        line.innerHTML = `<span>${letter}</span>`;
        ["x", "y", "z"].forEach((axis, k) => {
          line.appendChild(numberInput(vector[k], `${letter}${i + 1} ${axis}`, (v) => {
            vector[k] = v;
            edited();
          }));
        });
        cell.appendChild(line);
      }
      row.appendChild(cell);
      const tail = document.createElement("td");
      tail.className = "row-tail";
      const flag = document.createElement("span");
      flag.className = "outside";
      flag.textContent = "⚠";
      flag.title = T.outside;
      flag.setAttribute("aria-label", T.outside);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", T.remove(i + 1));
      remove.disabled = system.forces.length === 1;
      remove.addEventListener("click", () => {
        system.forces.splice(i, 1);
        system.points.splice(i, 1);
        buildForceRows();
        edited();
      });
      tail.append(flag, remove);
      row.appendChild(tail);
      nodes.forces.appendChild(row);
    });
    nodes.add.disabled = system.forces.length >= MAX_FORCES;
    nodes.add.title = nodes.add.disabled ? T.maxForces(MAX_FORCES) : "";
  }

  function markOutside() {
    [...nodes.forces.children].forEach((row, i) => row.classList.toggle("is-outside", !boxContains(system.box, system.points[i])));
  }

  function buildVectorInputs() {
    for (const [key, host] of Object.entries(nodes.vectors)) {
      host.innerHTML = "";
      const target = key === "box" ? system.box : system[key];
      const names = key === "box" ? ["a", "b", "c"] : ["x", "y", "z"];
      names.forEach((axis, k) => {
        host.appendChild(numberInput(target[k], `${key} ${axis}`, (v) => {
          if (key === "box" && !(v > 0)) return;
          target[k] = v;
          edited();
        }));
      });
    }
  }

  function edited() {
    caseKey = null;
    syncChips();
    recompute();
  }

  // ---------------------------------------------------------------- examples

  function buildCases() {
    for (const group of GROUP_ORDER) {
      const box = document.createElement("div");
      box.className = "case-group";
      box.innerHTML = `<p class="case-group-title">${T.groups[group]}</p>`;
      const chips = document.createElement("div");
      chips.className = "case-chips";
      for (const [key, item] of Object.entries(golden.cases)) {
        if (item.expected !== group) continue;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "chip";
        button.dataset.case = key;
        button.textContent = T.cases[key] ?? key;
        button.addEventListener("click", () => load(key));
        chips.appendChild(button);
      }
      box.appendChild(chips);
      nodes.cases.appendChild(box);
    }
  }

  function syncChips() {
    for (const chip of nodes.cases.querySelectorAll(".chip")) chip.setAttribute("aria-pressed", String(chip.dataset.case === caseKey));
  }

  function load(key) {
    const input = golden.cases[key].input;
    system = {
      forces: input.forces.map((f) => [...f]),
      points: input.points.map((p) => [...p]),
      Q: [...input.Q],
      A: [...input.A],
      u: [...input.u],
      box: [...input.box],
    };
    caseKey = key;
    const [elevation, azimuth] = golden.cases[key].view;
    scene.setFrame(frameFromAngles(elevation, azimuth));
    buildForceRows();
    buildVectorInputs();
    syncChips();
    recompute();
  }

  nodes.add.addEventListener("click", () => {
    if (system.forces.length >= MAX_FORCES) return;
    system.forces.push([0, 0, -1]);
    system.points.push([system.box[0] / 2, system.box[1] / 2, system.box[2]]);
    buildForceRows();
    edited();
  });

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

  buildCases();
  load("forca_binario");

  return {
    onChange(listener) {
      listeners.push(listener);
      listener(system, reduction, reduction ? null : nodes.status.textContent);
    },
    system: () => system,
    reduction: () => reduction,
    caseView: () => (caseKey ? golden.cases[caseKey].view : null),
    load,
    colors: theme,
  };
}
