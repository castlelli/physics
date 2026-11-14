import { createLab } from "./lab.js";
import { createAxisSection, createMinimumSection } from "./axis.js";
import { createProof } from "./proof.js";
import { createScene, frameFromAngles } from "./scene.js";
import { reduce } from "./model.js";
import { drawScales, figureTwo } from "./draw.js";
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

// The force + couple example with its central axis, turning slowly until the reader grabs it.
function setupHero(golden) {
  const item = golden.cases.forca_binario;
  const system = item.input;
  const r = reduce(system);
  const scales = drawScales(system, r);
  const canvas = document.getElementById("hero-scene");
  const scene = createScene(canvas, { frame: frameFromAngles(...item.view), gizmo: false });
  scene.setContent((colors) => figureTwo(system, r, colors, scales));
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
  const golden = await fetch(new URL("../data/golden.json", import.meta.url)).then((response) => response.json());
  setupHero(golden);
  const lab = createLab(golden);
  createAxisSection(lab);
  createMinimumSection(lab);
  createProof(golden, lab);
}

main();
