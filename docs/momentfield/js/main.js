import { createLab } from "./lab.js";
import { createAxialSection, createNormalSection } from "./sections.js";
import { createProof } from "./proof.js";
import { createScene, frameForAxis } from "./scene.js";
import { autoScale, sampleField } from "./model.js";
import { fieldContent } from "./field.js";
import { invalidateTheme, reducedMotion, theme, watchVisibility } from "./ui.js";
import { T } from "./i18n.js";

function setupTheme() {
  const toggle = document.querySelector("[data-theme-toggle]");
  const label = () => (toggle.textContent = theme().dark ? T.themeLight : T.themeDark);
  toggle.addEventListener("click", () => {
    const next = theme().dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (error) {
      // Storage can be blocked; the choice then lasts for this visit only.
    }
    invalidateTheme();
    label();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    invalidateTheme();
    label();
  });
  label();
}

// The F = (1, 2, 3) example, turning slowly until the reader grabs it.
function setupHero(report) {
  const item = report.cases.campo1;
  const c = item.config;
  const field = sampleField(
    { nPlanes: c.n_planes, planeSpacing: c.plane_spacing, angleStepDeg: c.angle_step_deg, nRadii: c.n_radii, radiusStep: c.radius_step },
    item.force_point,
    item.force,
  );
  const scales = autoScale(field);
  const canvas = document.getElementById("hero-scene");
  const scene = createScene(canvas, { frame: frameForAxis(field.basis.u), gizmo: false });
  scene.setContent((colors) => fieldContent(field, colors, { momentScale: scales.moment, forceScale: scales.force }));

  const spin = { on: !reducedMotion(), visible: true, last: 0 };
  const frame = (time) => {
    if (!spin.on || !spin.visible) return;
    const dt = spin.last ? Math.min(0.05, (time - spin.last) / 1000) : 0;
    spin.last = time;
    scene.spinAboutZ(dt * 0.3);
    requestAnimationFrame(frame);
  };
  scene.setSpin({ pause: () => (spin.on = false) });
  watchVisibility(canvas, (visible) => {
    spin.visible = visible;
    spin.last = 0;
    if (visible && spin.on) requestAnimationFrame(frame);
  });
}

async function main() {
  setupTheme();
  // resolved from this module, so the English page in en/ reads the same file
  const report = await fetch(new URL("../data/report.json", import.meta.url)).then((response) => response.json());
  setupHero(report);
  const lab = createLab(report);
  createNormalSection(lab);
  createAxialSection(lab);
  createProof(report, lab);
}

main();
