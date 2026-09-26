/* reel.js — a motion-reel project, scaffolded from the motion-reel skill.
 *
 * The whole film is one pure function of time: render(ctx, t, tf) paints the frame at
 * time t, and tf is the frame's own time, used for anything that must switch on a frame
 * boundary (cuts, on-screen counters). Nothing carries over between frames, so any
 * frame renders in any order, sub-frames average into real motion blur, and the film
 * can be scrubbed.
 *
 * Edit CONTENT (the story), THEME (the look) and SCENES (the order and the pacing).
 * Every number below is an invented placeholder: replace each with one read from your
 * source, and label anything illustrative on screen (see CONTENT.signal.tag).
 */
(function (root) {
'use strict';

// ================================================================== STORY
const CONTENT = {
  brand: 'ACME SIGNALS',
  asOf: 'DATA: 2026-09-01',
  locale: 'en-US',
  process: ['DISCOVER', 'ANALYSE', 'BUILD', 'REVIEW'],
  scale: {
    title: 'Pick a level.', sub: 'FROM CAUTIOUS TO BOLD', low: 'LOWER RISK', high: 'HIGHER RISK',
    levels: [
      { key: 'L1', name: 'Cautious', note: '1 month' },
      { key: 'L2', name: 'Careful', note: '3 months' },
      { key: 'L3', name: 'Balanced', note: '6 months' },
      { key: 'L4', name: 'Dynamic', note: '1 year' },
      { key: 'L5', name: 'Bold', note: '2+ years' },
    ],
  },
  mix: {
    title: 'The mix', sub: 'NEUTRAL WEIGHTS · A RANGE FOR GROWTH', parts: ['Core', 'Growth', 'Extras'],
    rows: [[90, 10, 0], [70, 25, 5], [50, 40, 10], [30, 55, 15], [15, 70, 15]], // one row per level; parts sum to 100
    ranges: [[0, 20], [15, 35], [30, 50], [45, 65], [60, 80]], // allowed range of the dive part, per level
    focus: 2, // the column the camera dives into
    divePart: 1, // the part it dives through; its colour becomes the next scene's ground
  },
  signal: {
    title: 'The signal', sub: 'DAILY · QUALITY, TREND AND MOMENTUM',
    inputs: [{ name: 'Quality', value: 0.5 }, { name: 'Trend', value: 0.35 }, { name: 'Momentum', value: -0.15 }],
    composite: 0.23, label: 'Composite',
    gauge: { title: 'Growth at level 3', range: [30, 50], neutral: 40, overshoot: 46.5, target: 45, rangeLabel: 'range', neutralLabel: 'neutral', targetLabel: 'target' },
    tag: 'ILLUSTRATION',
  },
  rank: {
    title: 'The ranking', sub: 'ONE SCORE · 1,000 ITEMS', axis: 'SCORE', top: 'TOP RATED',
    pillars: [{ name: 'QUALITY', weight: 40 }, { name: 'STABILITY', weight: 35 }, { name: 'VALUE', weight: 25 }],
    hist: [9, 15, 24, 33, 45, 57, 68, 76, 83, 86, 86, 83, 76, 68, 58, 47, 36, 26, 15, 9], // items per score bin, low to high: 1,000
  },
  check: {
    title: 'The check', sub: 'ONE PASS OVER EVERY ITEM', legend: 'Status',
    groups: [ // counts sum to the ranking's items
      { name: 'pass', count: 612, color: 'good' }, { name: 'watch', count: 214, color: 'warm' },
      { name: 'fail', count: 121, color: 'bad' }, { name: 'no data', count: 53, color: 'muted' },
    ],
    flag: 2, // the group that steps out of the sphere
  },
  result: {
    title: 'The result', sub: 'ONE MODEL MIX · LEVEL 3',
    center: { big: 'L3', name: 'Balanced', note: 'HORIZON 6 MONTHS' },
    classes: [{ name: 'Core', weight: 50, color: 'dark' }, { name: 'Growth', weight: 40, color: 'accent' }, { name: 'Extras', weight: 10, color: 'warm' }],
    items: [ // cls: index into classes
      { name: 'Core, short term', weight: 15, color: 'dark', cls: 0 },
      { name: 'Core, long term', weight: 25, color: 'slate', cls: 0 },
      { name: 'Core, global', weight: 10, color: 'steel', cls: 0 },
      { name: 'Growth, developed markets', weight: 30, color: 'accent', cls: 1 },
      { name: 'Growth, emerging markets', weight: 10, color: 'accent2', cls: 1 },
      { name: 'Extras, gold', weight: 10, color: 'warm', cls: 2 },
    ],
  },
  cards: [ // one per slot of the rhythm scene; a `quiet` card is held in silence
    { big: '5', label: 'levels', bg: 'accent' }, { big: '3', label: 'parts', bg: 'paper' }, { count: 1000, label: 'items', bg: 'dark' },
    { word: 'daily', label: 'SIGNALS', bg: 'soft' }, { word: 'weekly', label: 'RANKING', bg: 'accent' },
    { word: 'monthly', label: 'REPORT', bg: 'paper' }, { word: 'quarterly', label: 'REVIEW', bg: 'mid' }, { quiet: 'breathe.', bg: 'dark' },
  ],
  end: { name: 'Acme Signals', line: 'Built to last', recap: 'SCALE · MIX · SIGNAL · RANKING · CHECK · RESULT' },
};

// ================================================================== LOOK
const THEME = {
  dark: '#0F1B2D', deep: '#050B16', mid: '#1C2E4A', paper: '#FFFFFF', soft: '#E3ECFF',
  accent: '#1F6BFF', accent2: '#6B9BFF', sky: '#A9C4FF', slate: '#2C4466', steel: '#4E6C96',
  text: '#0E1726', muted: '#6B7280', warm: '#F29D0B', good: '#16A34A', bad: '#DC2626', white: '#FFFFFF',
};
const LIGHT = new Set(['paper', 'soft']); // grounds that take dark type
const FAM = { sans: 'Inter', mono: 'DM Mono' }; // must match fonts.css (scripts/fonts.py)
const HUD_ON = true;
const GRAIN = 0.035;

// ================================================================== SEQUENCE: one record per scene
// nom: bars the scene is choreographed for; bars: bars it gets (it stretches or squeezes
// to fit; all 1s makes a 15-second teaser); ground: the THEME key under it (null: the
// scene decides); step: its place in CONTENT.process (past the end: every step done);
// bloom and vig: finishing-pass strengths, glow for dark grounds only.
const SCENES = [
  { id: 'scale', name: 'SCALE', spec: '5 levels · from cautious to bold', step: 0, nom: 3, bars: 3, ground: 'dark', bloom: 0.22, vig: 0.3, draw: sScale },
  { id: 'mix', name: 'MIX', spec: 'three parts · a range for the middle one', step: 0, nom: 4, bars: 4, ground: 'paper', bloom: 0, vig: 0.05, draw: sMix },
  { id: 'signal', name: 'SIGNAL', spec: 'three inputs · one composite', step: 1, nom: 4, bars: 4, ground: null, bloom: 0.08, vig: 0.12, draw: sSignal },
  { id: 'rank', name: 'RANKING', spec: '1,000 items · one score', step: 1, nom: 4, bars: 4, ground: 'dark', bloom: 0.3, vig: 0.3, draw: sRank },
  { id: 'check', name: 'CHECK', spec: 'every item · one pass', step: 1, nom: 4, bars: 4, ground: 'deep', bloom: 0.42, vig: 0.35, draw: sCheck },
  { id: 'result', name: 'RESULT', spec: 'level 3 · 50 / 40 / 10', step: 2, nom: 4, bars: 4, ground: 'paper', bloom: 0, vig: 0.05, draw: sResult },
  { id: 'rhythm', name: 'RHYTHM', spec: 'daily · weekly · monthly · quarterly', step: 3, nom: 4, bars: 4, ground: null, bloom: 0, vig: 0.08, draw: sRhythm },
  { id: 'end', name: 'END', spec: 'Built to last.', step: 4, nom: 3, bars: 3, ground: 'dark', bloom: 0.25, vig: 0.35, draw: sEnd },
];
const at = Object.fromEntries(SCENES.map((s, i) => [s.id, i])); // scene index by id

// ================================================================== PACING
const W = 1920, H = 1080, FPS = 60;
const BPM = 128, BEAT = 60 / BPM, BAR = 4 * BEAT;
const ST = SCENES.reduce((acc, s, i) => (acc.push(acc[i] + s.bars * BAR), acc), [0]); // scene start times
const DUR = ST[SCENES.length];
const choreoLen = i => SCENES[i].nom * BAR; // the length scene i is choreographed for
const sceneLen = i => ST[i + 1] - ST[i]; // the length it actually gets
const pace = i => choreoLen(i) / sceneLen(i); // choreography seconds per real second
const absTime = (i, u) => ST[i] + u / pace(i); // choreography time u of scene i -> film time
const CARD = sceneLen(at.rhythm) / CONTENT.cards.length;
const QUIET = CONTENT.cards.findIndex(c => c.quiet);
const SIL = QUIET < 0 ? [ST[at.end], ST[at.end]] : [ST[at.rhythm] + QUIET * CARD, ST[at.rhythm] + (QUIET + 1) * CARD];
const GROOVE = [ST[at.mix], SIL[0]]; // the drums play from the second scene until the silence
const TAU = Math.PI * 2;

// ------------------------------------------------------------------ colour and number helpers
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const RGB = Object.fromEntries(Object.entries(THEME).map(([k, v]) => [k, hex(v)]));
const mixc = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const css = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const inkOn = key => (LIGHT.has(key) ? THEME.text : THEME.white);
const NUM = new Intl.NumberFormat(CONTENT.locale);
const SIGNED = new Intl.NumberFormat(CONTENT.locale, { minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'always' });
const fmt = n => NUM.format(n);
const signed = v => SIGNED.format(v).replace('-', '−');
const pct = v => `${fmt(v)}%`;

// ------------------------------------------------------------------ math
const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const E = {
  inCubic: x => x * x * x,
  outCubic: x => 1 - (1 - x) ** 3,
  inOutCubic: x => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2),
  outExpo: x => (x >= 1 ? 1 : 1 - 2 ** (-10 * x)),
  inExpo: x => (x <= 0 ? 0 : 2 ** (10 * x - 10)),
  inOutExpo: x => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 2 ** (20 * x - 10) / 2 : (2 - 2 ** (-20 * x + 10)) / 2),
};
// damped spring: seconds since release -> 0..1, overshooting on the way (f in Hz, d = decay)
const spring = (s, f = 3, d = 7) => (s <= 0 ? 0 : 1 - Math.exp(-d * s) * Math.cos(TAU * f * s));
const bump = (t, a, b, edge) => seg(t, a, a + edge) * (1 - seg(t, b - edge, b));
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
function mulberry32(a) {
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ------------------------------------------------------------------ drawing helpers
const G = {};
const mkCanvas = (w, h) => Object.assign(document.createElement('canvas'), { width: w, height: h });
function setFont(ctx, fam, size, weight = 400, spacing = 0) {
  ctx.font = `${Math.round(weight)} ${size}px "${fam}"`;
  ctx.letterSpacing = spacing + 'px';
}
function letters(ctx, text, fam, size, weight, tracking = 0) {
  const ch = [...text], ws = [];
  setFont(ctx, fam, size, weight);
  for (const c of ch) ws.push(ctx.measureText(c).width);
  const total = ws.reduce((a, b) => a + b, 0) + tracking * (ch.length - 1), xs = [];
  let x = -total / 2;
  for (let i = 0; i < ch.length; i++) { xs.push(x + ws[i] / 2); x += ws[i] + tracking; }
  return { ch, ws, xs, total };
}
function camera(ctx, z = 1, dx = 0, dy = 0, cx = W / 2, cy = H / 2) {
  ctx.translate(cx + dx, cy + dy);
  ctx.scale(z, z);
  ctx.translate(-cx, -cy);
}
// the half-time kick as the picture feels it: beat one and the and-of-two, within the groove
function kick(t) {
  if (t < GROOVE[0] || t >= GROOVE[1]) return 0;
  const u = (t - GROOVE[0]) % BAR, last = u >= 1.5 * BEAT ? 1.5 * BEAT : 0;
  return Math.exp(-(u - last) * 8);
}
const pump = t => 1 + 0.005 * kick(t);
// text rising out of a mask under its own baseline
function reveal(ctx, text, x, y, size, weight, col, s, opts = {}) {
  if (s <= 0) return;
  const e = E.outExpo(clamp(s / (opts.dur || 0.9)));
  setFont(ctx, opts.fam || FAM.sans, size, weight, opts.spacing || 0);
  ctx.save();
  ctx.beginPath(); ctx.rect(-W, y - size * 1.35, 3 * W, size * 1.35 + size * 0.3); ctx.clip();
  ctx.fillStyle = col; ctx.textAlign = opts.align || 'left'; ctx.globalAlpha *= clamp(s / 0.2);
  ctx.fillText(text, x, y + (1 - e) * size * 1.15);
  ctx.restore();
}
function typed(ctx, text, x, y, col, s, dur, opts = {}) {
  const n = Math.ceil(text.length * clamp(s / dur));
  if (n <= 0) return;
  setFont(ctx, FAM.mono, opts.size || 16, opts.weight || 400, opts.spacing ?? 3);
  ctx.textAlign = opts.align || 'left'; ctx.fillStyle = col;
  const a = ctx.globalAlpha; ctx.globalAlpha = a * (opts.alpha ?? 0.72);
  ctx.fillText(text.slice(0, n), x, y);
  ctx.globalAlpha = a;
}
function headline(ctx, title, sub, col, lt, at0) {
  reveal(ctx, title, 150, 250, 104, 700, col, lt - at0, { dur: 0.9 });
  if (sub) typed(ctx, sub, 153, 302, col, lt - at0 - 0.35, 0.6);
}
function flash(ctx, t, t0, amp, k, col = THEME.white) {
  if (t < t0) return;
  const a = amp * Math.exp(-(t - t0) * k);
  if (a < 0.004) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = a; ctx.fillStyle = col; ctx.fillRect(0, 0, W, H); ctx.restore();
}
// squash on contact, stretch along the fall
function drawBall(ctx, x, st, r, v0, col) {
  const stretch = 0.3 * Math.min(1, Math.abs(st.v) / v0), sq = st.sq;
  const rx = (r * (1 + 0.55 * sq)) / Math.sqrt(1 + stretch), ry = r * (1 - 0.45 * sq) * (1 + stretch);
  ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(x, sq > 0 ? st.y + r - ry : st.y, rx, ry, 0, 0, TAU); ctx.fill();
}
// a ball that falls, lands on c0, bounces to land again on c1, and settles with the same restitution
function makeBounce({ y0, rest, tDrop, c0, c1, sq }) {
  const h0 = rest - y0, g = (2 * h0) / (c0 - tDrop) ** 2, air0 = c1 - c0 - sq, h1 = (g * (air0 / 2) ** 2) / 2, e2 = h1 / h0;
  const contacts = [c0], vin = [Math.sqrt(2 * g * h0)], air = [];
  let h = h1, tc = c0;
  while (h > 1.2) { const a = 2 * Math.sqrt((2 * h) / g); air.push(a); tc += sq + a; contacts.push(tc); vin.push(Math.sqrt(2 * g * h)); h *= e2; }
  const v0 = vin[0];
  function state(t) {
    if (t < c0) { const s = Math.max(0, t - tDrop); return { y: y0 + 0.5 * g * s * s, v: g * s, sq: 0 }; }
    for (let k = 0; k < contacts.length; k++) {
      const tk = contacts[k];
      if (t < tk + sq) return { y: rest, v: 0, sq: (Math.sin(Math.PI * clamp((t - tk) / sq)) * vin[k]) / v0 };
      if (k < air.length && t < tk + sq + air[k]) { const s = t - tk - sq, up = (g * air[k]) / 2; return { y: rest - (up * s - 0.5 * g * s * s), v: -(up - g * s), sq: 0 }; }
    }
    return { y: rest, v: 0, sq: 0 };
  }
  return { state, contacts, v0, settle: tc + sq };
}
function wrap(ctx, text, maxW) {
  const out = [];
  let line = '';
  for (const w of text.split(' ')) { const tryL = line ? line + ' ' + w : w; if (ctx.measureText(tryL).width > maxW && line) { out.push(line); line = w; } else line = tryL; }
  if (line) out.push(line);
  return out;
}

// ================================================================== SCALE
// A ball hops along the levels, one hop per beat, each higher than the last: the arc
// is the risk. Then it rises, takes the accent colour and opens into the next scene.
const SC = { x0: 380, x1: 1540, FY: 690, R: 18 };
const SQ = 0.035; // how long a ball stays squashed on a contact
const B0 = { t0: 0.95, c0: 3 * BEAT, step: BEAT, settle: 0.22 };
// the hop contacts and the settle, in choreography time: the ball and the sound both read these
function scaleContacts() {
  const n = CONTENT.scale.levels.length, hops = Array.from({ length: n }, (_, k) => B0.c0 + k * B0.step);
  return { hops, settle: hops[n - 1] + SQ + B0.settle };
}
const levelX = (k, n) => (n > 1 ? SC.x0 + (k * (SC.x1 - SC.x0)) / (n - 1) : (SC.x0 + SC.x1) / 2);
const hopH = (k, n) => lerp(70, 290, n > 2 ? k / (n - 2) : 1);
function scaleBall(u) {
  const n = CONTENT.scale.levels.length, { t0, c0, step } = B0, y0 = -60, rest = SC.FY - SC.R;
  const g = (2 * (rest - y0)) / (c0 - t0) ** 2, v0 = g * (c0 - t0);
  if (u < c0) { const s = Math.max(0, u - t0); return { x: levelX(0, n), y: y0 + 0.5 * g * s * s, v: g * s, sq: 0, v0 }; }
  for (let k = 0; k < n; k++) {
    const ck = c0 + k * step, strength = Math.min(1, Math.sqrt((k === 0 ? rest - y0 : hopH(k - 1, n)) / 290));
    if (u < ck + SQ) return { x: levelX(k, n), y: rest, v: 0, sq: Math.sin(Math.PI * clamp((u - ck) / SQ)) * strength, v0 };
    if (k < n - 1 && u < c0 + (k + 1) * step) {
      const s0 = ck + SQ, T = c0 + (k + 1) * step - s0, f = (u - s0) / T, h = hopH(k, n);
      return { x: lerp(levelX(k, n), levelX(k + 1, n), f), y: rest - 4 * h * f * (1 - f), v: (-4 * h * (1 - 2 * f)) / T, sq: 0, v0 };
    }
  }
  const s1 = scaleContacts().settle, s0 = s1 - B0.settle, h = 28, xl = levelX(n - 1, n);
  if (u < s1) { const f = (u - s0) / (s1 - s0); return { x: xl, y: rest - 4 * h * f * (1 - f), v: (-4 * h * (1 - 2 * f)) / B0.settle, sq: 0, v0 }; }
  if (u < s1 + SQ) return { x: xl, y: rest, v: 0, sq: Math.sin(Math.PI * clamp((u - s1) / SQ)) * 0.3, v0 };
  return { x: xl, y: rest, v: 0, sq: 0, v0 };
}
function irisGeom(t) {
  if (t < ST[at.mix]) return { hole: 24 * E.outCubic(seg(t, absTime(at.scale, choreoLen(at.scale) - 0.45), ST[at.mix])), outer: 44 };
  const e = E.outExpo(seg(t, ST[at.mix], absTime(at.mix, 0.65))), hole = lerp(24, 1260, e);
  return { hole, outer: hole + lerp(20, 3, e) };
}
function sScale(ctx, t, lt) {
  const S = CONTENT.scale, n = S.levels.length, D = choreoLen(at.scale), FY = SC.FY, X = k => levelX(k, n);
  ctx.fillStyle = THEME.dark; ctx.fillRect(0, 0, W, H);
  const fade = 1 - 0.85 * seg(lt, D - 1.225, D - 0.725);
  ctx.globalAlpha = fade;
  headline(ctx, S.title, S.sub, THEME.white, lt, 0.25);
  const cx = (X(0) + X(n - 1)) / 2, half = (X(n - 1) - X(0)) / 2 + 70, e = E.outExpo(seg(lt, 0.1, 1.2));
  ctx.globalAlpha = 0.3 * fade; ctx.fillStyle = THEME.white;
  ctx.fillRect(cx - half * e, FY, 2 * half * e, 2);
  const gy = FY + 160, gr = ctx.createLinearGradient(X(0), 0, X(n - 1), 0);
  gr.addColorStop(0, css(RGB.sky, 0.35)); gr.addColorStop(1, THEME.accent);
  ctx.globalAlpha = fade * seg(lt, 0.9, 1.4); ctx.fillStyle = gr;
  ctx.fillRect(X(0) - 40, gy, (X(n - 1) - X(0) + 80) * E.outExpo(seg(lt, 0.9, 1.9)), 4);
  setFont(ctx, FAM.mono, 13, 400, 2); ctx.fillStyle = THEME.white; ctx.globalAlpha = 0.55 * fade * seg(lt, 1.3, 1.8);
  ctx.textAlign = 'left'; ctx.fillText(S.low, X(0) - 40, gy + 30);
  ctx.textAlign = 'right'; ctx.fillText(S.high, X(n - 1) + 40, gy + 30);
  // the spacing chart: where the ball was, every third frame
  ctx.fillStyle = THEME.sky; ctx.globalAlpha = 0.8 * fade;
  const { hops } = scaleContacts(), lastHop = hops[n - 1] + 0.3;
  for (let f = 3; f / FPS <= Math.min(lt, lastHop); f += 3) {
    const st = scaleBall(f / FPS);
    if (st.y < -10) continue;
    ctx.beginPath(); ctx.arc(st.x, st.y, 2.8, 0, TAU); ctx.fill();
  }
  ctx.textAlign = 'center';
  S.levels.forEach((lv, k) => {
    const x = X(k), ck = hops[k], hit = lt >= ck, ap = seg(lt, 0.5 + 0.12 * k, 0.9 + 0.12 * k) * fade;
    if (hit && lt < ck + 0.7) {
      const s = (lt - ck) / 0.7;
      ctx.globalAlpha = (1 - s) * 0.7 * fade; ctx.strokeStyle = THEME.sky; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, FY + 1, 10 + 64 * E.outCubic(s), 0, TAU); ctx.stroke();
    }
    ctx.globalAlpha = ap; ctx.lineWidth = 2; ctx.strokeStyle = THEME.white; ctx.fillStyle = THEME.accent;
    ctx.beginPath(); ctx.arc(x, FY + 1, 8 * (hit ? 0.8 + 0.2 * spring(lt - ck, 2, 6) : 1), 0, TAU);
    if (hit) ctx.fill();
    ctx.stroke();
    const lift = hit ? -6 * spring(lt - ck, 1.8, 7) : 0;
    ctx.fillStyle = THEME.white; ctx.globalAlpha = ap * (hit ? 1 : 0.55);
    setFont(ctx, FAM.mono, 17, 500, 2); ctx.fillText(lv.key, x, FY + 50 + lift);
    setFont(ctx, FAM.sans, 25, 600); ctx.fillText(lv.name, x, FY + 86 + lift);
    setFont(ctx, FAM.mono, 14, 400, 1); ctx.globalAlpha *= 0.7; ctx.fillText(lv.note, x, FY + 114 + lift);
  });
  ctx.globalAlpha = 1;
  if (t >= ST[at.mix]) { ctx.fillStyle = THEME.accent; ctx.beginPath(); ctx.arc(W / 2, H / 2, irisGeom(t).outer, 0, TAU); ctx.fill(); return; }
  const st = scaleBall(lt), rise = E.inOutCubic(seg(lt, D - 1.025, D - 0.525));
  drawBall(ctx, lerp(st.x, W / 2, rise), { y: lerp(st.y, H / 2, rise), v: st.v * (1 - rise), sq: st.sq * (1 - rise) }, lerp(SC.R, 44, rise), st.v0, css(mixc(RGB.white, RGB.accent, rise)));
}

// ================================================================== MIX
// One stacked column per level rises on a spring, each with the allowed range of one
// part beside it. The eye is led to the focus column, then the camera dives into it.
const PARTC = ['dark', 'accent', 'warm']; // THEME keys of the parts, in order
const T_MIX = { rise: 0.5, stagger: 0.22, dive: [1.5, 0.3] }; // dive: seconds before the scene's end
function mixGeom(n) {
  const pitch = Math.min(250, 1250 / n), w = pitch * 0.6;
  return { pitch, w, x0: (W - (n * w + (n - 1) * (pitch - w))) / 2, HC: 480, base: 820 };
}
function sMix(ctx, t, lt) {
  const M = CONTENT.mix, n = M.rows.length, D = choreoLen(at.mix), geo = mixGeom(n), colX = k => geo.x0 + k * geo.pitch;
  ctx.fillStyle = THEME.paper; ctx.fillRect(0, 0, W, H);
  const F = M.focus, P = M.divePart, row = M.rows[F];
  const fx = colX(F) + geo.w / 2, fy = geo.base - (geo.HC * (row.slice(0, P).reduce((a, b) => a + b, 0) + row[P] / 2)) / 100;
  const zE = E.inExpo(seg(lt, D - T_MIX.dive[0], D - T_MIX.dive[1])), mv = E.inOutCubic(seg(lt, D - T_MIX.dive[0], D - 0.6));
  camera(ctx, (1 + 0.02 * seg(lt, T_MIX.rise, D - T_MIX.dive[0])) * (1 + 24 * zE) * pump(t), (W / 2 - fx) * mv, (H / 2 - fy) * mv, fx, fy);
  const out = 1 - seg(lt, D - 1.55, D - 1.1), focus = E.inOutCubic(seg(lt, D - 3.1, D - 2.5));
  ctx.globalAlpha = out;
  headline(ctx, M.title, M.sub, THEME.text, lt, 0.35);
  setFont(ctx, FAM.sans, 20, 500);
  let lx = W - 150;
  for (let j = M.parts.length - 1; j >= 0; j--) {
    const name = M.parts[j], w = ctx.measureText(name).width, r = M.parts.length - 1 - j;
    ctx.globalAlpha = out * seg(lt, 0.8 + 0.12 * r, 1.2 + 0.12 * r);
    ctx.fillStyle = THEME.text; ctx.textAlign = 'left'; ctx.fillText(name, lx - w, 244);
    ctx.fillStyle = THEME[PARTC[j]]; ctx.fillRect(lx - w - 24, 228, 14, 14);
    lx -= w + 60;
  }
  M.rows.forEach((r, k) => {
    const x = colX(k), g = spring(lt - T_MIX.rise - T_MIX.stagger * k, 1.2, 6), a = k === F ? 1 : out * (1 - 0.6 * focus);
    if (g <= 0) return;
    const hTot = geo.HC * g;
    ctx.globalAlpha = a;
    ctx.save(); ctx.beginPath(); ctx.roundRect(x, geo.base - hTot, geo.w, hTot, [8, 8, 0, 0]); ctx.clip();
    let y = geo.base;
    r.forEach((v, j) => { const h = ((geo.HC * v) / 100) * g; if (h > 0) { ctx.fillStyle = THEME[PARTC[j]]; ctx.fillRect(x, y - h, geo.w, h); y -= h; } });
    ctx.fillStyle = THEME.paper; y = geo.base;
    r.forEach(v => { y -= ((geo.HC * v) / 100) * g; if (v > 0 && y > geo.base - hTot + 1) ctx.fillRect(x, y - 1.5, geo.w, 3); });
    ctx.restore();
    const la = seg(lt, 1.5 + 0.15 * k, 1.9 + 0.15 * k) * (lt > D - 1.6 ? 0 : a);
    if (la > 0) {
      let yy = geo.base;
      setFont(ctx, FAM.mono, 18, 500); ctx.textAlign = 'center'; ctx.globalAlpha = la;
      r.forEach((v, j) => { const h = (geo.HC * v) / 100; if (h >= 34) { ctx.fillStyle = PARTC[j] === 'warm' ? THEME.text : THEME.white; ctx.fillText(pct(v), x + geo.w / 2, yy - h / 2 + 6); } yy -= h; });
    }
    const lv = CONTENT.scale.levels[k] || { key: `#${k + 1}`, name: '' };
    ctx.globalAlpha = a * seg(lt, 0.6 + 0.2 * k, 1.1 + 0.2 * k); ctx.textAlign = 'center';
    setFont(ctx, FAM.mono, 16, 500, 2); ctx.fillStyle = THEME.muted; ctx.fillText(lv.key, x + geo.w / 2, geo.base + 40);
    setFont(ctx, FAM.sans, 22, k === F ? 700 : 600); ctx.fillStyle = k === F ? css(mixc(RGB.text, RGB.accent, focus)) : THEME.text;
    ctx.fillText(lv.name, x + geo.w / 2, geo.base + 70);
    const ca = a * seg(lt, 2.4 + 0.15 * k, 2.9 + 0.15 * k), rg = M.ranges[k];
    if (ca > 0 && rg) {
      const gx = x + geo.w + 22, yv = v => geo.base - (geo.HC * v) / 100;
      ctx.globalAlpha = ca * 0.18; ctx.fillStyle = THEME.text; ctx.fillRect(gx - 1, yv(100), 2, geo.HC);
      ctx.globalAlpha = ca * 0.3; ctx.fillStyle = THEME[PARTC[P]]; ctx.fillRect(gx - 4, yv(rg[1]), 8, Math.max(2, yv(rg[0]) - yv(rg[1])));
      ctx.globalAlpha = ca; ctx.fillStyle = THEME.text; ctx.fillRect(gx - 8, yv(r[P]) - 1.5, 16, 3);
      setFont(ctx, FAM.mono, 12, 400); ctx.fillStyle = THEME.muted; ctx.textAlign = 'center';
      ctx.fillText(rg[1] ? `${fmt(rg[0])}–${fmt(rg[1])}` : '0', gx, yv(rg[1]) - 10);
    }
  });
  ctx.globalAlpha = 1;
}

// ================================================================== SIGNAL
// Three inputs fold into one composite, which moves a weight inside its range and
// snaps to the grid. Illustrative numbers are labelled as such on screen.
const T_SIG = { inputs: 0.7, stagger: 0.25, fold: [2.9, 3.7], connector: [4.0, 4.6], slide: [4.5, 5.3], snap: 5.4 };
function sSignal(ctx, t, lt) {
  const S = CONTENT.signal, gz = S.gauge, ground = PARTC[CONTENT.mix.divePart], ink = inkOn(ground);
  ctx.fillStyle = THEME[ground]; ctx.fillRect(0, 0, W, H);
  camera(ctx, pump(t));
  headline(ctx, S.title, S.sub, ink, lt, 0.2);
  const AX0 = 500, AX1 = 1020, AC = (AX0 + AX1) / 2, AH = (AX1 - AX0) / 2, yC = 790, comp = S.composite;
  const fold = E.inOutCubic(seg(lt, ...T_SIG.fold));
  ctx.fillStyle = ink;
  S.inputs.forEach(({ name, value }, i) => {
    const at0 = T_SIG.inputs + T_SIG.stagger * i; // this input's bar starts growing
    const y = lerp(470 + 92 * i, yC, fold), g = E.outExpo(seg(lt, at0, at0 + 0.9)), val = lerp(value, comp, fold) * g;
    ctx.globalAlpha = seg(lt, at0 - 0.2, at0 + 0.2) * (1 - fold);
    setFont(ctx, FAM.sans, 30, 600); ctx.textAlign = 'left'; ctx.fillText(name, 150, y + 10);
    ctx.globalAlpha = 0.28 * seg(lt, 0.3, 0.8) * (i === 0 ? 1 : 1 - fold);
    ctx.fillRect(AX0, y - 1, AX1 - AX0, 2); ctx.fillRect(AC - 1, y - 14, 2, 28);
    if (g > 0) {
      ctx.globalAlpha = 1;
      const x0 = Math.min(AC, AC + val * AH), w = Math.abs(val * AH);
      ctx.beginPath(); ctx.roundRect(x0, y - 11, Math.max(2, w), 22, 11); ctx.fill();
      ctx.globalAlpha = seg(lt, at0 + 0.5, at0 + 0.9) * (1 - fold);
      setFont(ctx, FAM.mono, 19, 500); ctx.textAlign = value >= 0 ? 'left' : 'right';
      ctx.fillText(signed(value), AC + val * AH + (value >= 0 ? 18 : -18), y + 7);
    }
  });
  const ca = seg(lt, T_SIG.fold[1] - 0.2, T_SIG.fold[1] + 0.3);
  if (ca > 0) {
    ctx.globalAlpha = ca; setFont(ctx, FAM.sans, 30, 600); ctx.textAlign = 'left'; ctx.fillText(S.label, 150, yC + 10);
    setFont(ctx, FAM.mono, 20, 500); ctx.fillText(signed(comp), AC + comp * AH + 18, yC + 8);
    setFont(ctx, FAM.mono, 13, 400); ctx.globalAlpha = ca * 0.65; ctx.textAlign = 'center';
    [[-1, '−1'], [0, '0'], [1, '+1']].forEach(([v, s]) => ctx.fillText(s, AC + v * AH, yC + 40));
  }
  const GX0 = 1200, GX1 = 1770, GY = 640, gx = v => GX0 + ((GX1 - GX0) * v) / 100, ga = seg(lt, 1.2, 1.8);
  ctx.globalAlpha = ga; setFont(ctx, FAM.sans, 30, 600); ctx.textAlign = 'left'; ctx.fillText(gz.title, GX0, 500);
  if (S.tag) {
    setFont(ctx, FAM.mono, 12, 500, 3); ctx.textAlign = 'right';
    const tw = ctx.measureText(S.tag).width;
    ctx.globalAlpha = ga * 0.85; ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.roundRect(GX1 - tw - 14, 436, tw + 24, 28, 14); ctx.stroke(); ctx.fillText(S.tag, GX1 - 4, 455);
  }
  ctx.globalAlpha = ga * 0.3; ctx.fillRect(GX0, GY - 2, GX1 - GX0, 4);
  for (let v = 0; v <= 100; v += 5) { const major = v % 25 === 0; ctx.globalAlpha = ga * (major ? 0.55 : 0.3); ctx.fillRect(gx(v) - 1, GY + 10, 2, major ? 14 : 8); }
  setFont(ctx, FAM.mono, 13, 400); ctx.textAlign = 'center'; ctx.globalAlpha = ga * 0.65;
  [0, 25, 50, 75, 100].forEach(v => ctx.fillText(fmt(v), gx(v), GY + 46));
  const cb = seg(lt, 1.6, 2.2), [lo, hi] = gz.range;
  ctx.globalAlpha = cb * 0.2; ctx.fillRect(gx(lo), GY - 18, gx(hi) - gx(lo), 36);
  ctx.globalAlpha = cb * 0.7; ctx.fillRect(gx(lo) - 1, GY - 18, 2, 36); ctx.fillRect(gx(hi) - 1, GY - 18, 2, 36);
  ctx.globalAlpha = cb; setFont(ctx, FAM.mono, 14, 400); ctx.textAlign = 'left'; ctx.fillText(`${gz.rangeLabel} ${fmt(lo)}–${fmt(hi)}%`, gx(lo), GY - 32);
  ctx.globalAlpha = cb * 0.9; ctx.fillRect(gx(gz.neutral) - 1.5, GY - 24, 3, 48);
  setFont(ctx, FAM.mono, 14, 400); ctx.textAlign = 'center'; ctx.globalAlpha = cb * 0.8; ctx.fillText(`${gz.neutralLabel} ${pct(gz.neutral)}`, gx(gz.neutral), GY + 78);
  const cp = seg(lt, ...T_SIG.connector);
  if (cp > 0) {
    ctx.globalAlpha = 0.6; ctx.strokeStyle = ink; ctx.lineWidth = 2; ctx.setLineDash([1400 * cp, 1400]);
    ctx.beginPath(); ctx.moveTo(AC + comp * AH + 110, yC); ctx.bezierCurveTo(1110, yC, 1110, GY, gx(gz.neutral) - 34, GY); ctx.stroke(); ctx.setLineDash([]);
  }
  let v = gz.neutral + (gz.overshoot - gz.neutral) * E.outExpo(seg(lt, ...T_SIG.slide));
  if (lt > T_SIG.snap) v = lerp(gz.overshoot, gz.target, spring(lt - T_SIG.snap, 2.2, 7));
  const snap = seg(lt, T_SIG.snap, T_SIG.snap + 0.05) * (1 - seg(lt, T_SIG.snap + 0.5, T_SIG.snap + 0.9));
  if (snap > 0) { ctx.globalAlpha = snap; ctx.fillRect(gx(gz.target) - 1.5, GY + 6, 3, 26); }
  ctx.globalAlpha = cb; ctx.fillStyle = ink;
  ctx.beginPath(); ctx.arc(gx(v), GY, 14, 0, TAU); ctx.fill();
  ctx.fillStyle = THEME[ground]; ctx.beginPath(); ctx.arc(gx(v), GY, 5, 0, TAU); ctx.fill();
  const tl = seg(lt, T_SIG.snap + 0.05, T_SIG.snap + 0.4);
  if (tl > 0) { ctx.globalAlpha = tl; ctx.fillStyle = ink; setFont(ctx, FAM.mono, 16, 500); ctx.textAlign = 'center'; ctx.fillText(`${gz.targetLabel} ${pct(gz.target)}`, gx(gz.target), GY - 64); }
  ctx.globalAlpha = 1;
}

// ================================================================== RANKING
// One particle per item leaves a cloud and settles into the score distribution, left
// to right. The top fifth gets its stars, then every item lifts into the sphere.
const HIST = { base: 850, span: 1272 };
const SPH = { cx: 880, cy: 620, R: 370 };
const DNC = { cx: 760, cy: 590 }; // the result donut's centre, where the check ring lands
function sphereXY(k, r) { // r: film seconds since the check scene began (negative while items fly in)
  const p = G.sph[k], ry = 0.6 + 0.3 * r, rx = 0.32, cr = Math.cos(ry), sr = Math.sin(ry), cx = Math.cos(rx), sx = Math.sin(rx);
  const x1 = p[0] * cr + p[2] * sr, z1 = -p[0] * sr + p[2] * cr, y1 = p[1] * cx - z1 * sx, z2 = p[1] * sx + z1 * cx;
  const Z = z2 * SPH.R, s = 1300 / (1500 + Z);
  return [SPH.cx + x1 * SPH.R * s, SPH.cy + y1 * SPH.R * s, Z, s];
}
const T_RANK = { move: 0.9, land: 0.8, stars: 3.6, starStep: 0.12, fly: [1.2, 0.3] }; // fly: seconds before the end
const QCOL = ['#34507A', '#2B4FA8', THEME.accent, THEME.accent2, THEME.white]; // score fifths, low to high
function star(ctx, x, y, r) {
  ctx.beginPath();
  for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + (k * Math.PI) / 5, rr = k % 2 ? r * 0.45 : r; ctx.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)); }
  ctx.closePath(); ctx.fill();
}
function sRank(ctx, t, lt) {
  const R = CONTENT.rank, D = choreoLen(at.rank), I = G.items;
  ctx.fillStyle = THEME.dark; ctx.fillRect(0, 0, W, H);
  const flyAt = D - T_RANK.fly[0], deep = seg(lt, flyAt, D - 0.5);
  if (deep > 0) { ctx.globalAlpha = deep; ctx.fillStyle = THEME.deep; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
  camera(ctx, pump(t) * (1 + 0.02 * seg(lt, 1.0, flyAt) * (1 - E.inOutCubic(seg(lt, flyAt, D - 0.2)))), 0, 0, W / 2, 700);
  const out = 1 - seg(lt, flyAt - 0.1, flyAt + 0.3), x0 = I.x0, span = I.span;
  ctx.globalAlpha = out;
  headline(ctx, R.title, R.sub, THEME.white, lt, 0.2);
  const ax = seg(lt, 0.6, 1.2) * out;
  ctx.globalAlpha = ax * 0.3; ctx.fillStyle = THEME.white; ctx.fillRect(x0 - 12, HIST.base + 8, (span + 24) * E.outExpo(seg(lt, 0.6, 1.6)), 2);
  setFont(ctx, FAM.mono, 14, 400); ctx.textAlign = 'center'; ctx.globalAlpha = ax * 0.6;
  [0, 25, 50, 75, 100].forEach(s => { const x = x0 + (s / 100) * span; ctx.fillRect(x - 1, HIST.base + 10, 2, 8); ctx.fillText(fmt(s), x, HIST.base + 40); });
  setFont(ctx, FAM.mono, 13, 500, 3); ctx.textAlign = 'left'; ctx.globalAlpha = ax * 0.75; ctx.fillText(R.axis, x0 - 12, HIST.base + 72);
  if (seg(lt, 0.9, 1.5) > 0) {
    let bx = 1170;
    R.pillars.forEach(({ name, weight }, j) => {
      const segW = (600 * weight) / 100, e = E.outExpo(seg(lt, 0.9 + 0.2 * j, 1.7 + 0.2 * j));
      ctx.globalAlpha = out * [1, 0.75, 0.5][j % 3]; ctx.fillStyle = [THEME.white, THEME.sky, THEME.soft][j % 3];
      ctx.fillRect(bx, 222, (segW - 4) * e, 12);
      ctx.globalAlpha = out * e * 0.8; setFont(ctx, FAM.mono, 12, 500, 1); ctx.fillStyle = THEME.white; ctx.textAlign = 'center';
      ctx.fillText(`${name} ${fmt(weight)}%`, bx + segW / 2, 262);
      bx += segW;
    });
  }
  const stars = seg(lt, T_RANK.stars, T_RANK.stars + 0.3) * out, focus = seg(lt, T_RANK.stars - 0.1, T_RANK.stars + 0.2) * (1 - seg(lt, flyAt - 0.1, flyAt + 0.1));
  const fly = seg(lt, flyAt, D - T_RANK.fly[1]);
  for (let q = 0; q < 5; q++) {
    const idx = I.groups[q];
    ctx.fillStyle = css(mixc(hex(QCOL[q]), RGB.sky, fly), q < 4 ? 1 - 0.45 * focus : 1);
    ctx.globalAlpha = 1; ctx.beginPath();
    for (let j = 0; j < idx.length; j++) {
      const i = idx[j];
      const cxp = I.cx[i] + 14 * Math.sin(lt * 0.8 + I.ph[i]), cyp = I.cy[i] + 9 * Math.cos(lt * 0.7 + I.ph[i]);
      const m = E.inOutCubic(seg(lt, I.del[i], I.del[i] + T_RANK.move));
      let x = lerp(cxp, I.sx[i], m), y = lerp(cyp, I.sy[i], m);
      if (m > 0 && m < 1) { const dx = I.sx[i] - cxp, dy = I.sy[i] - cyp, L = Math.hypot(dx, dy) + 1e-6, sw = Math.sin(Math.PI * m) * 70 * I.sgn[i]; x += (-dy / L) * sw; y += (dx / L) * sw; }
      let z = lerp(5, I.dot, m);
      const f = E.inOutCubic(seg(lt, flyAt + I.sd[i], D - T_RANK.fly[1] + I.sd[i]));
      if (f > 0) { const [px, py, , s] = sphereXY(I.perm[i], t - ST[at.check]); x = lerp(x, px, f); y = lerp(y, py, f); z = lerp(z, 1.5 + 2.6 * s, f); }
      ctx.rect(x - z / 2, y - z / 2, z, z);
    }
    ctx.fill();
  }
  if (stars > 0) {
    const b0 = I.topFrom, sx0 = x0 + b0 * I.binW, sw = (I.bins - b0) * I.binW - 8, sy = HIST.base - I.topH - 60;
    ctx.fillStyle = THEME.white;
    for (let k = 0; k < 5; k++) {
      const sp = spring(lt - T_RANK.stars - T_RANK.starStep * k, 2, 7);
      if (sp <= 0) continue;
      ctx.globalAlpha = stars; star(ctx, sx0 + 26 + ((sw - 52) * k) / 4, sy, 13 * sp);
    }
    setFont(ctx, FAM.mono, 13, 500, 2); ctx.textAlign = 'center'; ctx.globalAlpha = stars * 0.8;
    ctx.fillText(R.top, sx0 + sw / 2, sy - 32);
  }
  ctx.globalAlpha = 1;
}

// ================================================================== CHECK
// The same items as a slowly turning sphere. A scan passes over it and every item
// takes its group's colour; the flagged group steps out. Then it all folds into a ring.
const T_CHECK = { scan: [1.0, 3.6], flag: 3.8, collapse: [1.15, 0.35], collapseStagger: 0.3 }; // collapse: before the end
function sCheck(ctx, t, lt) {
  const C = CONTENT.check, D = choreoLen(at.check), N = G.sph.length;
  ctx.fillStyle = THEME.deep; ctx.fillRect(0, 0, W, H);
  camera(ctx, pump(t));
  const out = 1 - seg(lt, D - T_CHECK.collapse[0] - 0.15, D - T_CHECK.collapse[0] + 0.25), scanEnd = T_CHECK.scan[1];
  ctx.globalAlpha = out;
  headline(ctx, C.title, C.sub, THEME.white, lt, 0.3);
  const silR = SPH.R * 0.9; // the sphere's projected silhouette: the scan stays inside it
  const scanY = lerp(SPH.cy - silR, SPH.cy + silR, E.inOutCubic(seg(lt, ...T_CHECK.scan)));
  const flag = spring(lt - T_CHECK.flag, 1.2, 5);
  const cls = G.cls, fills = [...C.groups.map(gr => THEME[gr.color] || THEME.muted), css(RGB.sky, 0.85), THEME.accent];
  const unscanned = C.groups.length, ringed = C.groups.length + 1;
  const pts = [];
  for (let k = 0; k < N; k++) {
    let [x, y, Z, s] = sphereXY(k, lt / pace(at.check));
    if (cls[k] === C.flag && lt > T_CHECK.flag) { const push = 1 + 0.09 * flag; x = SPH.cx + (x - SPH.cx) * push; y = SPH.cy + (y - SPH.cy) * push; }
    const lag = T_CHECK.collapseStagger * (k / N), m = E.inOutCubic(seg(lt, D - T_CHECK.collapse[0] + lag, D - T_CHECK.collapse[1] + lag));
    if (m > 0) { const a = (TAU * k) / N - Math.PI / 2; x = lerp(x, DNC.cx + 272 * Math.cos(a), m); y = lerp(y, DNC.cy + 272 * Math.sin(a), m); s = lerp(s, 0.95, m); Z = lerp(Z, 0, m); }
    pts.push([x, y, Z, s, m > 0.5 ? ringed : y < scanY || lt > scanEnd + 0.1 ? cls[k] : unscanned]);
  }
  for (const back of [true, false]) {
    for (let g = 0; g < fills.length; g++) {
      ctx.fillStyle = fills[g]; ctx.globalAlpha = back ? 0.45 : 1; ctx.beginPath();
      for (const [x, y, Z, s, gg] of pts) {
        if (gg !== g || (Z > 0) !== back) continue;
        const r = (2.6 + 4.2 * (s - 0.7)) * (gg === C.flag && lt > T_CHECK.flag ? 1 + 0.6 * Math.exp(-(lt - T_CHECK.flag) * 3) : 1);
        ctx.moveTo(x + r, y); ctx.arc(x, y, Math.max(0.8, r), 0, TAU);
      }
      ctx.fill();
    }
  }
  const sa = seg(lt, T_CHECK.scan[0] - 0.1, T_CHECK.scan[0] + 0.2) * (1 - seg(lt, scanEnd - 0.1, scanEnd + 0.2));
  if (sa > 0) {
    const dy = scanY - SPH.cy, rx = 1.08 * Math.sqrt(Math.max(0, silR * silR - dy * dy));
    ctx.globalAlpha = sa; ctx.strokeStyle = THEME.accent2; ctx.lineWidth = 2.5; ctx.shadowColor = THEME.accent; ctx.shadowBlur = 24;
    ctx.beginPath(); ctx.ellipse(SPH.cx, scanY, Math.max(1, rx), Math.max(1, rx * 0.16), 0, 0, TAU); ctx.stroke();
    ctx.shadowBlur = 0;
  }
  const lx = 1370;
  ctx.globalAlpha = out * seg(lt, scanEnd - 0.4, scanEnd); setFont(ctx, FAM.sans, 30, 700); ctx.fillStyle = THEME.white; ctx.textAlign = 'left';
  ctx.fillText(C.legend, lx, 450);
  C.groups.forEach(({ name, count, color }, k) => {
    const a = out * seg(lt, scanEnd - 0.2 + 0.18 * k, scanEnd + 0.2 + 0.18 * k), y = 510 + 50 * k;
    if (a <= 0) return;
    ctx.globalAlpha = a; ctx.fillStyle = THEME[color] || THEME.muted; ctx.beginPath(); ctx.arc(lx + 8, y - 8, 8, 0, TAU); ctx.fill();
    ctx.fillStyle = THEME.white; setFont(ctx, FAM.sans, 24, 500); ctx.textAlign = 'left'; ctx.fillText(name, lx + 32, y);
    setFont(ctx, FAM.mono, 20, 500); ctx.textAlign = 'right'; ctx.fillText(fmt(count), 1770, y);
  });
  ctx.globalAlpha = out * seg(lt, scanEnd + 0.6, scanEnd + 1.0) * 0.6; setFont(ctx, FAM.mono, 13, 400, 2); ctx.textAlign = 'left'; ctx.fillStyle = THEME.white;
  ctx.fillText(CONTENT.asOf, lx, 510 + 50 * C.groups.length + 30);
  ctx.globalAlpha = 1;
}

// ================================================================== RESULT
// The ring becomes the result: classes inside, items flying into place outside, the
// names on the right. During the hold each class steps forward in turn.
const DN = { r0: 150, r1: 212, r2: 224, r3: 318 };
const T_RES = { sweep: [0.2, 1.6], items: 0.9, itemStep: 0.2, lock: 0.25, focus: 3.2, focusLen: 1.0, flood: [1.1, 0.1] }; // flood: before the end
function ring(ctx, rin, rout, a0, a1, push = 0) {
  const am = (a0 + a1) / 2, ox = Math.cos(am) * push, oy = Math.sin(am) * push;
  ctx.beginPath(); ctx.arc(DNC.cx + ox, DNC.cy + oy, rout, a0, a1); ctx.arc(DNC.cx + ox, DNC.cy + oy, rin, a1, a0, true); ctx.closePath(); ctx.fill();
}
function sResult(ctx, t, lt) {
  const Rz = CONTENT.result, D = choreoLen(at.result);
  ctx.fillStyle = THEME.paper; ctx.fillRect(0, 0, W, H);
  camera(ctx, pump(t) * (1 + 0.015 * seg(lt, 1.0, D - T_RES.flood[0])), 0, 0, DNC.cx, DNC.cy);
  headline(ctx, Rz.title, Rz.sub, THEME.text, lt, 0.3);
  const focusOf = c => bump(lt, T_RES.focus + c * T_RES.focusLen, T_RES.focus + (c + 1) * T_RES.focusLen, 0.3);
  const anyFocus = Math.max(0, ...Rz.classes.map((_, c) => focusOf(c)));
  const rot = -Math.PI / 2 + 0.035 * lt, gap = 0.012, A = TAU * E.outExpo(seg(lt, ...T_RES.sweep));
  let a = 0;
  Rz.classes.forEach(({ weight, color }, c) => {
    const a0 = a, a1 = a + (TAU * weight) / 100, f = focusOf(c);
    a = a1;
    if (a0 >= A) return;
    ctx.globalAlpha = 1 - 0.55 * (anyFocus - f); ctx.fillStyle = THEME[color];
    ring(ctx, DN.r0, DN.r1, rot + a0 + gap, rot + Math.min(a1, A) - gap, 10 * E.inOutCubic(f));
  });
  a = 0;
  Rz.items.forEach(({ weight, color, cls }, k) => {
    const a0 = a, a1 = a + (TAU * weight) / 100, s = lt - T_RES.items - T_RES.itemStep * k, sp = spring(s, 1.0, 6), f = focusOf(cls);
    a = a1;
    if (sp <= 0) return;
    const off = 1 - sp;
    ctx.globalAlpha = seg(s, 0, 0.25) * (1 - 0.55 * (anyFocus - f)); ctx.fillStyle = THEME[color];
    ring(ctx, DN.r2 + 140 * off, DN.r3 + 140 * off, rot + a0 + gap - 0.6 * off, rot + a1 - gap - 0.6 * off, 10 * E.inOutCubic(f));
  });
  ctx.globalAlpha = seg(lt, 0.6, 1.1); ctx.textAlign = 'center'; ctx.fillStyle = THEME.text;
  setFont(ctx, FAM.sans, 72, 800); ctx.fillText(Rz.center.big, DNC.cx, DNC.cy + 8);
  setFont(ctx, FAM.sans, 26, 500); ctx.fillText(Rz.center.name, DNC.cx, DNC.cy + 48);
  setFont(ctx, FAM.mono, 13, 400, 2); ctx.fillStyle = THEME.muted; ctx.fillText(Rz.center.note, DNC.cx, DNC.cy + 78);
  const LX = 1180, RX = 1770;
  let y = 340, row = 0;
  Rz.classes.forEach((cl, c) => {
    const dim = 1 - 0.55 * (anyFocus - focusOf(c));
    const ra = seg(lt, 1.6 + 0.14 * row, 2.0 + 0.14 * row), dx = 40 * (1 - E.outExpo(ra));
    ctx.globalAlpha = ra * dim; ctx.fillStyle = THEME.text; setFont(ctx, FAM.sans, 22, 700); ctx.textAlign = 'left'; ctx.fillText(cl.name, LX + dx, y);
    setFont(ctx, FAM.mono, 18, 500); ctx.textAlign = 'right'; ctx.fillText(pct(cl.weight), RX + dx, y);
    y += 38; row++;
    for (const it of Rz.items.filter(item => item.cls === c)) {
      const rb = seg(lt, 1.6 + 0.14 * row, 2.0 + 0.14 * row), dx2 = 40 * (1 - E.outExpo(rb));
      ctx.globalAlpha = rb * dim; ctx.fillStyle = THEME[it.color]; ctx.fillRect(LX + dx2, y - 13, 12, 12);
      setFont(ctx, FAM.sans, 19, 400); ctx.fillStyle = THEME.text; ctx.textAlign = 'left';
      const lines = wrap(ctx, it.name, RX - LX - 90);
      lines.forEach((ln, j) => ctx.fillText(ln, LX + 24 + dx2, y + j * 26));
      setFont(ctx, FAM.mono, 16, 400); ctx.fillStyle = THEME.muted; ctx.textAlign = 'right'; ctx.fillText(pct(it.weight), RX + dx2, y);
      y += 26 * lines.length + 12; row++;
    }
    y += 14;
  });
  ctx.globalAlpha = 1;
  const fr = 2200 * E.inOutCubic(seg(lt, D - T_RES.flood[0], D - T_RES.flood[1])), next = CONTENT.cards[0];
  if (fr > 1) { ctx.fillStyle = THEME[next ? next.bg : 'accent']; ctx.beginPath(); ctx.arc(DNC.cx, DNC.cy, fr, 0, TAU); ctx.fill(); }
}

// ================================================================== RHYTHM
// Cards on the beat grid: the numbers, then the cadence. A `quiet` card is the
// punchline: one small word, held in total silence.
const COUNT_SPAN = 0.55; // share of a card the count-up takes
const COUNT_TICKS = 40; // odometer ticks the soundtrack plays while the number climbs
const cardIndex = tf => clamp(Math.floor((tf - ST[at.rhythm]) / CARD + 1e-6), 0, CONTENT.cards.length - 1);
function sRhythm(ctx, t, lt, tf) {
  const k = cardIndex(tf), c = t - (ST[at.rhythm] + k * CARD), cd = CONTENT.cards[k], fg = inkOn(cd.bg);
  ctx.fillStyle = THEME[cd.bg]; ctx.fillRect(0, 0, W, H);
  if (cd.quiet) {
    setFont(ctx, FAM.sans, 40, 400); ctx.fillStyle = fg; ctx.textAlign = 'center';
    ctx.globalAlpha = seg(c, 0, 0.16 * CARD); ctx.fillText(cd.quiet, W / 2, H / 2 + 14); ctx.globalAlpha = 1;
    return;
  }
  const rv = 0.3 * CARD;
  camera(ctx, 1.03 - 0.03 * E.outExpo(clamp(c / (0.48 * CARD))) + 0.02 * clamp(c / CARD));
  const e = E.outExpo(clamp(c / rv));
  ctx.textAlign = 'center';
  let lineY;
  if (cd.word) {
    let size = 180;
    setFont(ctx, FAM.sans, size, 800, -4);
    const w = ctx.measureText(cd.word).width;
    if (w > 1500) size *= 1500 / w;
    const yb = H / 2 + 40;
    reveal(ctx, cd.word, W / 2, yb, size, 800, fg, c, { dur: rv, align: 'center', spacing: -4 });
    ctx.globalAlpha = e * 0.85; setFont(ctx, FAM.mono, 24, 500, 5); ctx.fillStyle = fg; ctx.fillText(cd.label, W / 2, yb + 92);
    lineY = yb + 130;
  } else {
    const yb = H / 2 + 70, size = 320;
    if (cd.count) {
      const n = Math.round(cd.count * E.outExpo(clamp(c / (CARD * COUNT_SPAN))));
      setFont(ctx, FAM.sans, size, 800, -6);
      const wFinal = ctx.measureText(fmt(cd.count)).width;
      reveal(ctx, fmt(n), W / 2 + wFinal / 2, yb, size, 800, fg, c, { dur: rv, align: 'right', spacing: -6 });
    } else reveal(ctx, cd.big, W / 2, yb, size, 800, fg, c, { dur: rv, align: 'center', spacing: -6 });
    ctx.globalAlpha = e; setFont(ctx, FAM.sans, 60, 600); ctx.fillStyle = fg; ctx.textAlign = 'center'; ctx.fillText(cd.label, W / 2, yb + 110);
    lineY = yb + 160;
  }
  ctx.globalAlpha = 0.25; ctx.fillStyle = fg; ctx.fillRect(W / 2 - 180, lineY, 360, 3);
  ctx.globalAlpha = 1; ctx.fillRect(W / 2 - 180, lineY, 360 * clamp(c / CARD), 3);
}

// ================================================================== END
// The name on the downbeat after the silence; the ball from the first scene returns to
// land as the full stop of the closing line.
const T_END = { drop: 1.35, contacts: [4 * BEAT, 5 * BEAT], recap: [2.6, 0.8], fade: 0.725 }; // contacts on beats 5 and 6; fade: before the end
function sEnd(ctx, t, lt) {
  const En = G.end, D = choreoLen(at.end);
  ctx.fillStyle = THEME.dark; ctx.fillRect(0, 0, W, H);
  camera(ctx, lerp(1.04, 1, E.outExpo(seg(lt, 0, 1.6))) * (1 + 0.015 * seg(lt, 1.0, D - 0.6)), 0, 0, W / 2, En.yb);
  setFont(ctx, FAM.sans, En.fs, 700, -2); ctx.fillStyle = THEME.white; ctx.textAlign = 'center';
  ctx.save(); ctx.beginPath(); ctx.rect(0, En.yb - En.fs * 1.3, W, En.fs * 1.3 + En.fs * 0.3); ctx.clip();
  En.L.ch.forEach((ch, i) => {
    const s = lt - 0.03 * i;
    if (s <= 0) return;
    ctx.globalAlpha = clamp(s / 0.2); ctx.fillText(ch, W / 2 + En.L.xs[i], En.yb + (1 - E.outExpo(clamp(s / 0.9))) * En.fs * 0.95);
  });
  ctx.restore();
  ctx.globalAlpha = 1;
  const ul = (E.outExpo(seg(lt, 0.6, 1.5)) * En.L.total) / 2;
  if (ul > 0.5) { ctx.fillStyle = THEME.accent; ctx.fillRect(W / 2 - ul, En.yb + 40, ul * 2, 5); }
  setFont(ctx, FAM.sans, 64, 300); ctx.fillStyle = THEME.white; ctx.textAlign = 'left';
  ctx.save(); ctx.beginPath(); ctx.rect(0, En.yb2 - 90, W, 115); ctx.clip();
  En.words.forEach((wd, k) => {
    const s = lt - (0.9 + 0.12 * k);
    if (s > 0) ctx.fillText(wd.text, wd.x, En.yb2 + (1 - E.outExpo(seg(s, 0, 0.8))) * 90);
  });
  ctx.restore();
  const b = En.ball, st = b.state(lt);
  if (lt > T_END.drop) drawBall(ctx, lerp(En.px + 220, En.px, E.outCubic(clamp((lt - T_END.drop) / (b.settle - T_END.drop)))), st, En.rP, b.v0, THEME.accent);
  ctx.globalAlpha = 1;
  typed(ctx, En.recap, W / 2 - En.recapW / 2, En.yb + 270, THEME.white, lt - T_END.recap[0], T_END.recap[1], { spacing: 4, alpha: 0.6 });
  flash(ctx, t, ST[at.end], 0.1, 6);
  const fo = E.inCubic(seg(lt, D - T_END.fade, D));
  if (fo > 0) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = fo; ctx.fillStyle = THEME.dark; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
}

// ================================================================== transitions
function sceneIdx(tf) { for (let i = SCENES.length - 1; i > 0; i--) if (tf >= ST[i] - 1e-9) return i; return 0; }
function drawScene(ctx, i, t, tf) { ctx.save(); SCENES[i].draw(ctx, t, (t - ST[i]) * pace(i), tf); ctx.restore(); }
function clipCircle(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.clip(); }
const PUSH = Math.min(0.9, 0.12 * sceneLen(at.signal));
const TRANS = [
  { a: absTime(at.scale, choreoLen(at.scale) - 0.45), b: absTime(at.mix, 0.7), draw(ctx, t, tf) { // the ball becomes a ring, the ring an iris
    drawScene(ctx, at.scale, t, tf);
    const g = irisGeom(t);
    if (g.hole > 0.3) { ctx.save(); clipCircle(ctx, W / 2, H / 2, g.hole); drawScene(ctx, at.mix, t, tf); ctx.restore(); }
  } },
  { a: ST[at.rank] - PUSH, b: ST[at.rank] + 0.02, draw(ctx, t, tf) { // push up
    const e = E.inOutExpo(seg(t, ST[at.rank] - PUSH, ST[at.rank]));
    ctx.save(); ctx.translate(0, -H * e); drawScene(ctx, at.signal, t, tf); ctx.restore();
    ctx.save(); ctx.translate(0, H * (1 - e)); drawScene(ctx, at.rank, t, tf); ctx.restore();
  } },
  { a: ST[at.result], b: absTime(at.result, 1.05), draw(ctx, t, tf) { // the ring of items opens into the result
    drawScene(ctx, at.check, t, tf);
    const r = 1500 * E.inOutCubic(seg(t, ST[at.result], absTime(at.result, 1.0)));
    if (r > 0.3) { ctx.save(); clipCircle(ctx, DNC.cx, DNC.cy, r); drawScene(ctx, at.result, t, tf); ctx.restore(); }
  } },
];

// ================================================================== HUD
const pad2 = n => String(n).padStart(2, '0');
function hudInk(i, tf) {
  if (i === at.rhythm) { const cd = CONTENT.cards[cardIndex(tf)]; return cd.quiet ? null : inkOn(cd.bg); }
  return inkOn(SCENES[i].ground || PARTC[CONTENT.mix.divePart]);
}
function drawHud(ctx, t, tf) {
  if (!HUD_ON) return;
  const i = sceneIdx(tf), col = hudInk(i, tf);
  const a = 0.9 * seg(t, 0.06, 0.5) * (1 - seg(t, DUR - 0.8, DUR - 0.2));
  if (!col || a <= 0) return;
  const sc = SCENES[i];
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = a; ctx.fillStyle = col; ctx.textBaseline = 'alphabetic';
  setFont(ctx, FAM.mono, 15, 500, 3); ctx.textAlign = 'left'; ctx.fillText(CONTENT.brand, 84, 76);
  const steps = CONTENT.process, sep = '  —  ';
  setFont(ctx, FAM.mono, 14, 500, 3);
  const parts = [];
  steps.forEach((s, k) => { parts.push([s, k]); if (k < steps.length - 1) parts.push([sep, -1]); });
  let x = W - 84;
  for (let p = parts.length - 1; p >= 0; p--) {
    const [txt, k] = parts[p], w = ctx.measureText(txt).width;
    x -= w;
    ctx.globalAlpha = a * (k < 0 ? 0.3 : sc.step >= steps.length || k === sc.step ? 1 : k < sc.step ? 0.6 : 0.3);
    ctx.fillText(txt, x, 76);
    if (k === sc.step) { ctx.globalAlpha = a; ctx.fillRect(x, 86, w - 3, 2); }
  }
  const since = tf - ST[i], idx = `${pad2(i + 1)} / ${pad2(SCENES.length)}`;
  ctx.globalAlpha = a; setFont(ctx, FAM.mono, 15, 500, 3); ctx.textAlign = 'left';
  ctx.fillText(idx, 84, H - 92);
  ctx.fillText(sc.name.slice(0, Math.ceil(sc.name.length * seg(since, 0, 0.3))), 84 + ctx.measureText(idx).width + 20, H - 92);
  setFont(ctx, FAM.mono, 14, 400, 1.5); ctx.globalAlpha = a * 0.62;
  ctx.fillText(sc.spec.slice(0, Math.ceil(sc.spec.length * seg(since, 0.1, 0.7))), 84, H - 64);
  ctx.textAlign = 'right'; setFont(ctx, FAM.mono, 14, 400, 2); ctx.fillText(CONTENT.asOf, W - 84, H - 64);
  const x0 = W / 2 - 240, x1 = W / 2 + 240, y = H - 78, ph = x0 + ((x1 - x0) * tf) / DUR;
  ctx.globalAlpha = a * 0.3; ctx.fillRect(x0, y - 0.75, x1 - x0, 1.5);
  for (let k = 0; k <= SCENES.length; k++) ctx.fillRect(x0 + ((x1 - x0) * ST[k]) / DUR - 0.75, y - 4, 1.5, 8);
  ctx.globalAlpha = a; ctx.fillRect(x0, y - 1, ph - x0, 2); ctx.fillRect(ph - 3, y - 6, 6, 12);
  ctx.restore();
}

// ================================================================== render
function render(ctx, t, tf = t) {
  t = clamp(t, 0, DUR - 1e-6); tf = clamp(tf, 0, DUR - 1e-6);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
  const tr = TRANS.find(x => tf >= x.a && tf < x.b);
  if (tr) tr.draw(ctx, t, tf); else drawScene(ctx, sceneIdx(tf), t, tf);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  drawHud(ctx, t, tf);
}

// ------------------------------------------------------------------ finishing pass (after the motion blur)
function post(src, dst, tf) {
  const o = dst.getContext('2d'), sc = SCENES[sceneIdx(tf)];
  o.setTransform(1, 0, 0, 1, 0, 0); o.globalAlpha = 1; o.filter = 'none';
  o.globalCompositeOperation = 'copy'; o.drawImage(src, 0, 0);
  if (sc.bloom > 0) {
    const b = G.bloom.getContext('2d');
    b.globalCompositeOperation = 'copy'; b.filter = 'blur(6px)'; b.drawImage(dst, 0, 0, W / 4, H / 4); b.filter = 'none';
    o.globalCompositeOperation = 'screen'; o.globalAlpha = sc.bloom; o.drawImage(G.bloom, 0, 0, W, H); o.globalAlpha = 1;
  }
  if (GRAIN > 0) {
    const f = Math.round(tf * FPS), pat = o.createPattern(G.grain[f % G.grain.length], 'repeat');
    pat.setTransform(new DOMMatrix([2, 0, 0, 2, (hash(f) * 512) | 0, (hash(f + 99) * 512) | 0]));
    o.globalCompositeOperation = 'overlay'; o.globalAlpha = GRAIN; o.fillStyle = pat; o.fillRect(0, 0, W, H);
  }
  const vg = o.createRadialGradient(W / 2, H / 2, H * 0.42, W / 2, H / 2, H * 1.08), d = RGB.deep;
  vg.addColorStop(0, css(d, 0)); vg.addColorStop(1, css(d, 1));
  o.globalCompositeOperation = 'source-over'; o.globalAlpha = sc.vig; o.fillStyle = vg; o.fillRect(0, 0, W, H);
  o.globalAlpha = 1;
}

// ------------------------------------------------------------------ init
function initItems() {
  const hist = CONTENT.rank.hist, bins = hist.length, N = hist.reduce((a, b) => a + b, 0), rnd = mulberry32(11), F32 = () => new Float32Array(N);
  const I = { cx: F32(), cy: F32(), sx: F32(), sy: F32(), ph: F32(), del: F32(), sgn: F32(), sd: F32(), bin: new Uint16Array(N), perm: new Uint32Array(N) };
  I.bins = bins; I.span = HIST.span; I.binW = HIST.span / bins; I.x0 = (W - HIST.span) / 2;
  const perRow = Math.max(1, Math.floor((I.binW - 6) / 14)), rowsMax = Math.ceil(Math.max(...hist) / perRow);
  const pitch = Math.max(4, Math.min(14, Math.floor(330 / rowsMax), (I.binW - 6) / perRow));
  I.dot = pitch - 4; I.topFrom = Math.floor(bins * 0.8);
  I.topH = Math.ceil(Math.max(...hist.slice(I.topFrom)) / perRow) * pitch;
  let i = 0;
  hist.forEach((n, b) => {
    for (let j = 0; j < n; j++, i++) {
      I.bin[i] = b;
      I.sx[i] = I.x0 + b * I.binW + (j % perRow) * pitch + pitch / 2; I.sy[i] = HIST.base - pitch / 2 - Math.floor(j / perRow) * pitch;
      const a = rnd() * TAU, r = Math.sqrt(rnd());
      I.cx[i] = W / 2 + Math.cos(a) * r * 560; I.cy[i] = 560 + Math.sin(a) * r * 240;
      I.ph[i] = rnd() * TAU; I.del[i] = 1.0 + (b / Math.max(1, bins - 1)) + 0.25 * rnd(); I.sgn[i] = rnd() < 0.5 ? -1 : 1; I.sd[i] = rnd() * 0.3;
    }
  });
  const order = [...Array(N).keys()];
  for (let k = N - 1; k > 0; k--) { const j = Math.floor(rnd() * (k + 1)); [order[k], order[j]] = [order[j], order[k]]; }
  order.forEach((p, k) => { I.perm[k] = p; });
  I.groups = [0, 1, 2, 3, 4].map(q => Int32Array.from([...Array(N).keys()].filter(k => Math.min(4, Math.floor((5 * I.bin[k]) / bins)) === q)));
  return I;
}
function initSphere(N) {
  const sph = [];
  for (let k = 0; k < N; k++) {
    const y = 1 - (2 * (k + 0.5)) / N, r = Math.sqrt(1 - y * y), th = k * Math.PI * (3 - Math.sqrt(5));
    sph.push([Math.cos(th) * r, y, Math.sin(th) * r]);
  }
  const groups = CONTENT.check.groups, rnd = mulberry32(5), cls = [];
  groups.forEach(({ count }, g) => { for (let j = 0; j < count && cls.length < N; j++) cls.push(g); });
  while (cls.length < N) cls.push(groups.length - 1);
  for (let k = cls.length - 1; k > 0; k--) { const j = Math.floor(rnd() * (k + 1)); [cls[k], cls[j]] = [cls[j], cls[k]]; }
  return { sph, cls };
}
function initEnd(x) {
  const e = CONTENT.end, fs = 128, L = letters(x, e.name, FAM.sans, fs, 700, -2), yb = 480, yb2 = yb + 160, rP = 7;
  setFont(x, FAM.sans, 64, 300);
  const words = e.line.split(' '), sp = x.measureText(' ').width, ws = words.map(w => x.measureText(w).width);
  const tot = ws.reduce((a, b) => a + b, 0) + sp * (words.length - 1);
  let cx = W / 2 - tot / 2 - 8;
  const pos = words.map((w, i) => { const o = { text: w, x: cx }; cx += ws[i] + sp; return o; });
  const ball = makeBounce({ y0: -30, rest: yb2 - rP, tDrop: T_END.drop, c0: T_END.contacts[0], c1: T_END.contacts[1], sq: SQ });
  setFont(x, FAM.mono, 16, 400, 4);
  return { fs, L, yb, yb2, rP, px: W / 2 - tot / 2 - 8 + tot + 5 + rP, ball, words: pos, recap: e.recap, recapW: x.measureText(e.recap).width };
}
// the cue sheet: score.py places every sound from these film times. Every entry reads the same
// timing record its scene animates with, so re-timing a scene moves its sound with it.
function cueSheet() {
  const r = v => +v.toFixed(4), countAt = CONTENT.cards.findIndex(c => c.count), end = i => choreoLen(i);
  const win = (i, a, b) => [r(absTime(i, a)), r(absTime(i, b))];
  const { hops, settle } = scaleContacts();
  const countStart = ST[at.rhythm] + countAt * CARD, countLen = COUNT_SPAN * CARD;
  const invOutExpo = y => (y >= 1 ? 1 : -Math.log2(1 - y) / 10); // when outExpo reaches y
  return {
    bpm: BPM, scenes: SCENES.map(s => s.id), bars: SCENES.map(s => s.bars), starts: ST.map(r), silence: SIL.map(r), groove: GROOVE.map(r),
    scale: hops.map(u => r(absTime(at.scale, u))), scaleSettle: r(absTime(at.scale, settle)),
    arrive: r(ST[at.mix]),
    columns: CONTENT.mix.rows.map((_, k) => r(absTime(at.mix, T_MIX.rise + T_MIX.stagger * k))),
    dive: win(at.mix, end(at.mix) - T_MIX.dive[0], end(at.mix) - T_MIX.dive[1]), cut: r(ST[at.signal]),
    inputs: CONTENT.signal.inputs.map((_, i) => r(absTime(at.signal, T_SIG.inputs + T_SIG.stagger * i))),
    fold: r(absTime(at.signal, T_SIG.fold[0])), connector: r(absTime(at.signal, T_SIG.connector[0])),
    slide: win(at.signal, ...T_SIG.slide), snap: r(absTime(at.signal, T_SIG.snap)), push: [r(ST[at.rank] - PUSH), r(ST[at.rank])],
    landings: Array.from(G.items.del, d => r(absTime(at.rank, d + T_RANK.land))),
    stars: [0, 1, 2, 3, 4].map(k => r(absTime(at.rank, T_RANK.stars + T_RANK.starStep * k))),
    fly: [r(absTime(at.rank, end(at.rank) - T_RANK.fly[0])), r(ST[at.check])],
    scan: win(at.check, ...T_CHECK.scan), flag: r(absTime(at.check, T_CHECK.flag)),
    collapse: win(at.check, end(at.check) - T_CHECK.collapse[0], end(at.check) - T_CHECK.collapse[1] + T_CHECK.collapseStagger),
    iris: r(ST[at.result]), sweep: r(absTime(at.result, T_RES.sweep[0])),
    items: CONTENT.result.items.map((_, k) => r(absTime(at.result, T_RES.items + T_RES.itemStep * k + T_RES.lock))),
    focus: CONTENT.result.classes.map((_, c) => r(absTime(at.result, T_RES.focus + c * T_RES.focusLen))),
    flood: win(at.result, end(at.result) - T_RES.flood[0], end(at.result) - T_RES.flood[1]),
    cards: CONTENT.cards.map((_, k) => r(ST[at.rhythm] + k * CARD)), quiet: QUIET,
    count: countAt < 0 ? null : [r(countStart), r(countStart + countLen)],
    countTicks: countAt < 0 ? [] : Array.from({ length: COUNT_TICKS }, (_, k) => r(countStart + countLen * invOutExpo((k + 1) / COUNT_TICKS))),
    end: r(ST[at.end]), endBall: G.end.ball.contacts.map(c => r(absTime(at.end, c))), fade: [r(absTime(at.end, end(at.end) - T_END.fade)), r(DUR)],
  };
}
async function init() {
  if (document.fonts) {
    const sample = 'Aa1 ąćęłńóśźżĄĆĘŁŃÓŚŹŻäöüßéèàç'; // pulls in the latin-ext faces too
    await Promise.all(['800 100px "' + FAM.sans + '"', '300 100px "' + FAM.sans + '"', '400 20px "' + FAM.mono + '"', '500 20px "' + FAM.mono + '"'].map(f => document.fonts.load(f, sample)));
  }
  const x = mkCanvas(64, 64).getContext('2d');
  G.items = initItems();
  const s = initSphere(G.items.cx.length); G.sph = s.sph; G.cls = s.cls;
  G.end = initEnd(x);
  G.bloom = mkCanvas(W / 4, H / 4);
  G.grain = [0, 1, 2, 3].map(k => {
    const cv = mkCanvas(256, 256), cx = cv.getContext('2d'), im = cx.createImageData(256, 256), r = mulberry32(100 + k);
    for (let i = 0; i < 256 * 256; i++) { const v = clamp((r() + r() + r() - 1.5) * 95 + 128, 0, 255) | 0; im.data[i * 4] = im.data[i * 4 + 1] = im.data[i * 4 + 2] = v; im.data[i * 4 + 3] = 255; }
    cx.putImageData(im, 0, 0);
    return cv;
  });
  return cueSheet();
}

root.Reel = {
  W, H, FPS, DUR, init, render, post,
  scenes: () => SCENES.map((s, i) => ({ id: s.id, name: s.name, start: ST[i], dur: sceneLen(i) })),
};
})(typeof window !== 'undefined' ? window : globalThis);
