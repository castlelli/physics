// Small 3D renderer on a 2D canvas: orthographic camera, painter's sorting by depth, arrows
// (double-headed for moments), dashed lines and labels. Orthographic, so parallel stays parallel.

import { add, cross, dot, norm, rotate, scale, sub } from "./model.js";
import { fitCanvas, onResize, onThemeChange, pointerPosition, theme } from "./ui.js";

const Z = [0, 0, 1];

// Camera frame from elevation and azimuth in degrees (matplotlib's convention).
export function frameFromAngles(elevation, azimuth) {
  const e = (elevation * Math.PI) / 180;
  const a = (azimuth * Math.PI) / 180;
  const back = [Math.cos(e) * Math.cos(a), Math.cos(e) * Math.sin(a), Math.sin(e)];
  const right = normalize(cross(Z, back));
  return { right, up: cross(back, right) };
}

// Starting view for a field: 50° away from the line of action, so the planes of poles open up
// instead of being seen edge-on, with world z kept upright on the screen when possible.
export function frameForAxis(u, preferred = frameFromAngles(22, -60)) {
  const look = cross(preferred.right, preferred.up);
  let side = sub(look, scale(u, dot(look, u)));
  if (norm(side) < 1e-6) side = sub(Z, scale(u, dot(Z, u)));
  if (norm(side) < 1e-6) side = [1, 0, 0];
  side = normalize(side);
  const angle = (50 * Math.PI) / 180;
  const back = normalize(add(scale(u, Math.cos(angle)), scale(side, Math.sin(angle))));
  let right = cross(Z, back);
  right = norm(right) < 1e-6 ? normalize(cross(u, back)) : normalize(right);
  return { right, up: cross(back, right) };
}

function normalize(v) {
  return scale(v, 1 / norm(v));
}

export function createScene(canvas, options = {}) {
  const interactive = options.interactive ?? true;
  let frame = options.frame ?? frameFromAngles(22, -60);
  let homeFrame = frame;
  let zoom = 1;
  let build = () => ({ items: [], bounds: [], pickables: [] });
  let content = { items: [], bounds: [], pickables: [] };
  let fit = { centre: [0, 0, 0], radius: 1 };
  let message = "";
  let projected = [];
  let pending = false;
  let spin = null;

  // ---------------------------------------------------------------- projection

  function back() {
    return cross(frame.right, frame.up);
  }

  function project(p, view) {
    const r = sub(p, fit.centre);
    return [view.cx + dot(r, frame.right) * view.k, view.cy - dot(r, frame.up) * view.k, dot(r, view.back)];
  }

  function view(width, height) {
    const k = ((Math.min(width, height) * 0.46) / fit.radius) * zoom;
    return { cx: width / 2, cy: height / 2, k, back: back() };
  }

  // Centre and radius of the content's bounding sphere: the fit does not change as the camera turns.
  function refit() {
    const points = content.bounds;
    if (!points.length) return;
    const lo = [Infinity, Infinity, Infinity];
    const hi = [-Infinity, -Infinity, -Infinity];
    for (const p of points) for (let i = 0; i < 3; i++) (lo[i] = Math.min(lo[i], p[i])), (hi[i] = Math.max(hi[i], p[i]));
    const centre = scale(add(lo, hi), 0.5);
    let radius = 1e-9;
    for (const p of points) radius = Math.max(radius, norm(sub(p, centre)));
    fit = { centre, radius };
  }

  // ---------------------------------------------------------------- drawing

  function draw() {
    pending = false;
    const { ctx, width, height } = fitCanvas(canvas);
    const colors = theme();
    ctx.clearRect(0, 0, width, height);
    if (message) {
      ctx.fillStyle = colors.ink3;
      ctx.font = `15px ${colors.sans}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      wrapText(ctx, message, width / 2, height / 2, Math.min(360, width - 40), 22);
      return;
    }
    const v = view(width, height);
    const queue = [];
    for (const item of content.items) {
      if (item.kind === "segment" && item.split) {
        // long lines (the line of action) are cut into pieces so each piece sorts on its own depth
        for (let i = 0; i < item.split; i++) {
          const a = add(item.a, scale(sub(item.b, item.a), i / item.split));
          const b = add(item.a, scale(sub(item.b, item.a), (i + 1) / item.split));
          queue.push({ ...item, a, b, pa: project(a, v), pb: project(b, v) });
        }
      } else if (item.kind === "segment" || item.kind === "arrow") {
        queue.push({ ...item, pa: project(item.a, v), pb: project(item.b, v) });
      } else {
        queue.push({ ...item, pp: project(item.p, v) });
      }
    }
    const depth = (q) => (q.pp ? q.pp[2] : (q.pa[2] + q.pb[2]) / 2) + (q.lift ?? 0) * fit.radius;
    queue.sort((a, b) => depth(a) - depth(b));

    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const q of queue) paint(ctx, q);
    if (options.gizmo !== false) gizmo(ctx, height, colors);

    projected = content.pickables.map((p) => ({ id: p.id, at: project(p.p, v) }));
  }

  function paint(ctx, q) {
    ctx.globalAlpha = q.alpha ?? 1;
    if (q.kind === "segment") {
      ctx.strokeStyle = q.color;
      ctx.lineWidth = q.width ?? 1.4;
      ctx.setLineDash(q.dash ?? []);
      ctx.beginPath();
      ctx.moveTo(q.pa[0], q.pa[1]);
      ctx.lineTo(q.pb[0], q.pb[1]);
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (q.kind === "arrow") {
      arrow(ctx, q);
    } else if (q.kind === "dot") {
      ctx.fillStyle = q.color;
      ctx.beginPath();
      ctx.arc(q.pp[0], q.pp[1], q.radius ?? 3, 0, 2 * Math.PI);
      ctx.fill();
      if (q.ring) {
        ctx.strokeStyle = q.ring;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(q.pp[0], q.pp[1], (q.radius ?? 3) + 4, 0, 2 * Math.PI);
        ctx.stroke();
      }
    } else if (q.kind === "glyph") {
      glyph(ctx, q);
    } else if (q.kind === "text") {
      ctx.fillStyle = q.color;
      ctx.font = `${q.size ?? 14}px ${theme().sans}`;
      ctx.textAlign = q.align ?? "left";
      ctx.textBaseline = "middle";
      ctx.fillText(q.text, q.pp[0] + (q.offset?.[0] ?? 0), q.pp[1] + (q.offset?.[1] ?? 0));
    }
    ctx.globalAlpha = 1;
  }

  function arrow(ctx, q) {
    const dx = q.pb[0] - q.pa[0];
    const dy = q.pb[1] - q.pa[1];
    const length = Math.hypot(dx, dy);
    ctx.strokeStyle = q.color;
    ctx.fillStyle = q.color;
    ctx.lineWidth = q.width ?? 1.8;
    if (length < 0.5) return;
    const head = Math.min(q.head ?? 10, 0.45 * length);
    const ux = dx / length;
    const uy = dy / length;
    const baseX = q.pb[0] - ux * head;
    const baseY = q.pb[1] - uy * head;
    ctx.beginPath();
    ctx.moveTo(q.pa[0], q.pa[1]);
    ctx.lineTo(baseX + ux * 1, baseY + uy * 1);
    ctx.stroke();
    const half = head * 0.42;
    ctx.beginPath();
    ctx.moveTo(q.pb[0], q.pb[1]);
    ctx.lineTo(baseX - uy * half, baseY + ux * half);
    ctx.lineTo(baseX + uy * half, baseY - ux * half);
    ctx.closePath();
    ctx.fill();
    if (q.double && length > 2.4 * head) {
      // second head just behind the first: the engineering convention for a moment vector
      const bx = baseX - ux * head * 0.85;
      const by = baseY - uy * head * 0.85;
      const ax = bx - ux * head;
      const ay = by - uy * head;
      ctx.beginPath();
      ctx.moveTo(bx, by);
      ctx.lineTo(ax - uy * half, ay + ux * half);
      ctx.lineTo(ax + uy * half, ay - ux * half);
      ctx.closePath();
      ctx.fill();
    }
  }

  // ⊙ for a vector toward the reader, ⊗ for one going away.
  function glyph(ctx, q) {
    const [x, y] = q.pp;
    const r = Math.max(q.radius, 3);
    ctx.strokeStyle = q.color;
    ctx.fillStyle = q.color;
    ctx.lineWidth = q.width ?? 1.6;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.stroke();
    if (q.outward) {
      ctx.beginPath();
      ctx.arc(x, y, Math.max(1.8, r * 0.18), 0, 2 * Math.PI);
      ctx.fill();
    } else {
      const k = r / Math.SQRT2;
      ctx.beginPath();
      ctx.moveTo(x - k, y - k);
      ctx.lineTo(x + k, y + k);
      ctx.moveTo(x - k, y + k);
      ctx.lineTo(x + k, y - k);
      ctx.stroke();
    }
  }

  function gizmo(ctx, height, colors) {
    const origin = [30, height - 30];
    const axes = [
      ["x", [1, 0, 0]],
      ["y", [0, 1, 0]],
      ["z", [0, 0, 1]],
    ].map(([name, e]) => ({ name, x: dot(e, frame.right), y: dot(e, frame.up), z: dot(e, back()) }));
    axes.sort((a, b) => a.z - b.z);
    ctx.font = `13px ${colors.mono}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const a of axes) {
      ctx.strokeStyle = colors.ink3;
      ctx.fillStyle = colors.ink3;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.moveTo(origin[0], origin[1]);
      ctx.lineTo(origin[0] + a.x * 18, origin[1] - a.y * 18);
      ctx.stroke();
      ctx.fillText(a.name, origin[0] + a.x * 27, origin[1] - a.y * 27);
    }
  }

  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = text.split(" ");
    const lines = [];
    let line = "";
    for (const word of words) {
      const trial = line ? `${line} ${word}` : word;
      if (ctx.measureText(trial).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else line = trial;
    }
    lines.push(line);
    lines.forEach((l, i) => ctx.fillText(l, x, y + (i - (lines.length - 1) / 2) * lineHeight));
  }

  function request() {
    if (!pending) {
      pending = true;
      requestAnimationFrame(draw);
    }
  }

  // ---------------------------------------------------------------- interaction

  function turn(dx, dy) {
    const angleX = dx * 0.008;
    const angleY = dy * 0.008;
    let { right, up } = frame;
    // horizontal drag: about the vertical of the screen; vertical drag: about its horizontal
    right = rotate(right, up, -angleX);
    up = rotate(up, right, -angleY);
    // re-orthonormalize so rounding does not accumulate over long drags
    const r = normalize(right);
    const u = normalize(sub(up, scale(r, dot(up, r))));
    frame = { right: r, up: u };
    request();
  }

  if (interactive) {
    let drag = null;
    canvas.addEventListener("pointerdown", (event) => {
      drag = { x: event.clientX, y: event.clientY, moved: 0, id: event.pointerId };
      canvas.setPointerCapture(event.pointerId);
      spin?.pause?.();
    });
    canvas.addEventListener("pointermove", (event) => {
      if (drag && drag.id === event.pointerId) {
        const dx = event.clientX - drag.x;
        const dy = event.clientY - drag.y;
        drag.moved += Math.abs(dx) + Math.abs(dy);
        drag.x = event.clientX;
        drag.y = event.clientY;
        if (drag.moved > 3) {
          canvas.classList.add("dragging");
          turn(dx, dy);
        }
      } else if (options.onPick) {
        const [x, y] = pointerPosition(event, canvas);
        canvas.classList.toggle("over-pole", nearest(x, y) !== null);
      }
    });
    const release = (event) => {
      if (!drag || drag.id !== event.pointerId) return;
      if (drag.moved <= 3 && options.onPick) {
        const [x, y] = pointerPosition(event, canvas);
        options.onPick(nearest(x, y));
      }
      drag = null;
      canvas.classList.remove("dragging");
    };
    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", () => {
      drag = null;
      canvas.classList.remove("dragging");
    });
    canvas.addEventListener(
      "wheel",
      (event) => {
        if (!event.ctrlKey && !event.metaKey && !options.wheelZoom) return;
        event.preventDefault();
        zoom = Math.min(4, Math.max(0.4, zoom * Math.exp(-event.deltaY * 0.0015)));
        request();
      },
      { passive: false },
    );
    canvas.addEventListener("dblclick", () => api.reset());
  }

  function nearest(x, y) {
    let best = null;
    let bestDistance = 16;
    let bestDepth = -Infinity;
    for (const p of projected) {
      const distance = Math.hypot(p.at[0] - x, p.at[1] - y);
      // among poles under the pointer, the one nearest the reader wins
      if (distance < bestDistance - 4 || (distance < 16 && Math.abs(distance - bestDistance) <= 4 && p.at[2] > bestDepth)) {
        best = p.id;
        bestDistance = distance;
        bestDepth = p.at[2];
      }
    }
    return best;
  }

  onResize(canvas, request);
  onThemeChange(() => api.rebuild());

  const api = {
    // builder(colors) returns { items, bounds, pickables }; it runs again on theme changes.
    setContent(builder, { keepFit = false } = {}) {
      build = builder;
      message = "";
      content = build(theme());
      if (!keepFit) refit();
      request();
    },
    rebuild() {
      if (!message) content = build(theme());
      request();
    },
    setMessage(text) {
      message = text;
      content = { items: [], bounds: [], pickables: [] };
      request();
    },
    setFrame(next, { home = true } = {}) {
      frame = { right: normalize(next.right), up: normalize(next.up) };
      if (home) homeFrame = frame;
      request();
    },
    frame: () => frame,
    reset() {
      frame = homeFrame;
      zoom = 1;
      request();
    },
    zoomBy(factor) {
      zoom = Math.min(4, Math.max(0.4, zoom * factor));
      request();
    },
    // Turntable about world z, for the hero and the lab's "girar".
    spinAboutZ(radians) {
      frame = { right: rotate(frame.right, Z, radians), up: rotate(frame.up, Z, radians) };
      request();
    },
    setSpin(controller) {
      spin = controller;
    },
    redraw: request,
  };
  return api;
}
