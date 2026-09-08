'use strict';
// Comic Carousel Generator GUI. Vanilla JS: a queue of scans, a results table, and a box editor.

const token = document.querySelector('meta[name="token"]').content;
const $ = (id) => document.getElementById(id);
const SVG = 'http://www.w3.org/2000/svg';
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

async function api(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Token': token },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json().catch(() => ({ error: response.statusText }));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function say(text) { $('status').textContent = text; }

// ---- settings remembered per browser
const review = $('review');
const parent = $('parent');
try {
  review.checked = localStorage.getItem('review') === '1';
  parent.value = localStorage.getItem('parent') || '';
} catch (e) { /* storage unavailable: defaults are fine */ }
review.onchange = () => { try { localStorage.setItem('review', review.checked ? '1' : '0'); } catch (e) { /* ignore */ } };
parent.onchange = () => { try { localStorage.setItem('parent', parent.value); } catch (e) { /* ignore */ } };

// ---- results table
const tbody = $('results').tBodies[0];
const rows = [];

function addRow(path) {
  const tr = tbody.insertRow();
  const name = path.split(/[\\/]/).pop();
  tr.insertCell().textContent = name;
  tr.insertCell().textContent = '';
  tr.insertCell().textContent = 'Waiting';
  tr.insertCell();
  const entry = { path, name, tr, state: 'waiting' };
  rows.push(entry);
  return entry;
}

function setResult(entry, state, text, actions) {
  entry.state = state;
  entry.tr.cells[2].textContent = text;
  const cell = entry.tr.cells[3];
  cell.textContent = '';
  for (const [label, handler] of actions || []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.onclick = handler;
    cell.appendChild(button);
  }
  summarize();
}

function summarize() {
  const n = rows.length;
  if (!n) return;
  const done = rows.filter((r) => r.state === 'exported').length;
  const look = rows.filter((r) => r.state === 'review' || r.state === 'failed').length;
  const parts = [`${n} scan${n === 1 ? '' : 's'}.`];
  if (done) parts.push(`${done} exported.`);
  if (look) parts.push(`${look} need${look === 1 ? 's' : ''} a look.`);
  say(parts.join(' '));
}

function exported(entry, r) {
  entry.tr.cells[1].textContent = r.panels;
  setResult(entry, 'exported', `Exported to ${r.dir_name} (${r.layout})`, [
    ['Reveal', () => api('/api/reveal', { dir: r.dir }).catch((e) => say(e.message))],
    ['Review', () => enqueue(entry.path, true, entry)],
  ]);
}

// ---- queue
const queue = [];
let busy = false;

$('browse').onclick = async () => {
  say('Choosing…');
  try {
    const { paths } = await api('/api/pick');
    if (!paths.length) { say('Nothing chosen.'); return; }
    for (const path of paths) enqueue(path, false);
  } catch (e) { say(e.message); }
};

function enqueue(path, forceReview, entry) { queue.push({ path, forceReview, entry }); run(); }

async function run() {
  if (busy) return;
  busy = true;
  while (queue.length) {
    const { path, forceReview, entry } = queue.shift();
    await handle(path, forceReview, entry);
  }
  busy = false;
  summarize();
}

async function handle(path, forceReview, existing) {
  const entry = existing || addRow(path);  // a retry reuses its row instead of stacking a stale one
  setResult(entry, 'working', 'Looking for panels…');
  say(`Working on ${entry.name}…`);
  try {
    const r = await api('/api/process', { path, parent: parent.value, review: forceReview || review.checked });
    if (r.status === 'exported') { exported(entry, r); return; }
    entry.tr.cells[1].textContent = r.panels;
    setResult(entry, 'review', r.reasons.length ? `Needs a look: ${r.reasons.join('; ')}` : 'Waiting for you');
    const result = await edit(r);
    if (result) exported(entry, result); else setResult(entry, 'skipped', 'Skipped');
  } catch (e) {
    setResult(entry, 'failed', `Failed: ${e.message}`, [['Try again', () => enqueue(path, false, entry)]]);
  }
}

// ---- editor
const editor = $('editor');
const overlay = $('overlay');
const preview = $('preview');
const list = $('list');
const thumbs = $('thumbs');
const layoutSelect = $('layout');
let ed = null; // { id, w, h, boxes, selected, resolve }

function edit(r) {
  return new Promise((resolve) => {
    ed = { id: r.id, w: r.w, h: r.h, boxes: r.boxes.map((b) => ({ ...b })), selected: -1, resolve };
    $('editor-name').textContent = r.reasons.length ? `${r.name} — ${r.reasons.join('; ')}.` : r.name;
    layoutSelect.textContent = '';
    for (const name of r.layouts) {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      layoutSelect.appendChild(option);
    }
    layoutSelect.value = 'auto';
    overlay.setAttribute('viewBox', `0 0 ${r.w} ${r.h}`);
    preview.src = `/api/preview/${r.id}.jpg`;
    thumbs.textContent = '';
    editor.hidden = false;
    editor.scrollIntoView({ block: 'start' });
    draw();
    renderSoon();
  });
}

function finish(result) {
  editor.hidden = true;
  const { resolve } = ed;
  ed = null;
  resolve(result);
}

$('cancel').onclick = () => finish(null);
$('export').onclick = async () => {
  $('export').disabled = true;
  try {
    finish(await api('/api/export', { id: ed.id, boxes: ed.boxes, layout: layoutSelect.value, parent: parent.value }));
  } catch (e) { say(e.message); } finally { $('export').disabled = false; }
};
$('add').onclick = () => {
  const w = Math.round(ed.w * 0.3);
  const h = Math.round(ed.h * 0.3);
  ed.boxes.push({ x: Math.round((ed.w - w) / 2), y: Math.round((ed.h - h) / 2), w, h });
  ed.selected = ed.boxes.length - 1;
  changed();
};
layoutSelect.onchange = renderSoon;

function changed() { draw(); renderSoon(); }

function el(tag, attrs) {
  const node = document.createElementNS(SVG, tag);
  for (const key in attrs) node.setAttribute(key, attrs[key]);
  return node;
}

function draw() {
  overlay.textContent = '';
  list.textContent = '';
  const handle = Math.max(ed.w, ed.h) / 45;  // comfortable grab target at any zoom
  ed.boxes.forEach((b, i) => {
    const rect = el('rect', { x: b.x, y: b.y, width: b.w, height: b.h, 'data-index': i, 'data-part': 'body' });
    if (i === ed.selected) rect.setAttribute('data-selected', '');
    overlay.appendChild(rect);
    const label = el('text', { x: b.x + handle * 0.8, y: b.y + handle * 2.4, 'font-size': handle * 2 });
    label.textContent = i + 1;
    overlay.appendChild(label);
    const corners = { nw: [b.x, b.y], ne: [b.x + b.w, b.y], sw: [b.x, b.y + b.h], se: [b.x + b.w, b.y + b.h] };
    for (const part in corners) {
      const [cx, cy] = corners[part];
      overlay.appendChild(el('rect', { x: cx - handle / 2, y: cy - handle / 2, width: handle, height: handle, 'data-index': i, 'data-part': part }));
    }
    const li = document.createElement('li');
    li.textContent = `Panel ${i + 1} · ${b.w} × ${b.h} px `;
    for (const [label2, handler] of [['Up', () => move(i, -1)], ['Down', () => move(i, 1)], ['Remove', () => remove(i)]]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label2;
      button.onclick = handler;
      li.appendChild(button);
    }
    list.appendChild(li);
  });
}

function remove(i) { ed.boxes.splice(i, 1); ed.selected = -1; changed(); }
function move(i, d) {
  const j = i + d;
  if (j < 0 || j >= ed.boxes.length) return;
  [ed.boxes[i], ed.boxes[j]] = [ed.boxes[j], ed.boxes[i]];
  ed.selected = j;
  changed();
}

function point(evt) {
  const p = new DOMPoint(evt.clientX, evt.clientY).matrixTransform(overlay.getScreenCTM().inverse());
  return { x: p.x, y: p.y };
}

let drag = null;
overlay.addEventListener('pointerdown', (evt) => {
  if (!ed) return;
  const target = evt.target;
  if (!(target instanceof SVGRectElement)) { ed.selected = -1; draw(); return; }
  const index = Number(target.dataset.index);
  ed.selected = index;
  drag = { index, part: target.dataset.part, start: point(evt), box: { ...ed.boxes[index] } };
  overlay.setPointerCapture(evt.pointerId);
  draw();
});
overlay.addEventListener('pointermove', (evt) => {
  if (!drag || !ed) return;
  const p = point(evt);
  const dx = Math.round(p.x - drag.start.x);
  const dy = Math.round(p.y - drag.start.y);
  const b = drag.box;
  const n = ed.boxes[drag.index];
  const min = 40;
  if (drag.part === 'body') {
    n.x = clamp(b.x + dx, 0, ed.w - b.w);
    n.y = clamp(b.y + dy, 0, ed.h - b.h);
  } else {
    let x0 = b.x, y0 = b.y, x1 = b.x + b.w, y1 = b.y + b.h;
    if (drag.part.includes('w')) x0 = clamp(b.x + dx, 0, x1 - min);
    if (drag.part.includes('e')) x1 = clamp(b.x + b.w + dx, x0 + min, ed.w);
    if (drag.part.includes('n')) y0 = clamp(b.y + dy, 0, y1 - min);
    if (drag.part.includes('s')) y1 = clamp(b.y + b.h + dy, y0 + min, ed.h);
    n.x = x0; n.y = y0; n.w = x1 - x0; n.h = y1 - y0;
  }
  draw();
});
overlay.addEventListener('pointerup', () => { if (drag) { drag = null; renderSoon(); } });
overlay.addEventListener('pointercancel', () => { drag = null; });

document.addEventListener('keydown', (evt) => {
  if (!ed || ed.selected < 0 || (evt.key !== 'Delete' && evt.key !== 'Backspace')) return;
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  evt.preventDefault();
  remove(ed.selected);
});

// ---- live thumbnails
let timer = 0;
let serial = 0;
function renderSoon() { clearTimeout(timer); timer = setTimeout(renderNow, 300); }
async function renderNow() {
  if (!ed) return;
  const id = ++serial;
  const current = ed;
  try {
    const r = await api('/api/render', { id: ed.id, boxes: ed.boxes, layout: layoutSelect.value });
    if (id !== serial || ed !== current) return;
    thumbs.textContent = '';
    r.panels.forEach((src, i) => thumbs.appendChild(thumb(src, `panel_${String(i + 1).padStart(2, '0')}.png`)));
    thumbs.appendChild(thumb(r.summary, `summary.png (${r.layout})`));
  } catch (e) { say(e.message); }
}
function thumb(src, caption) {
  const li = document.createElement('li');
  const figure = document.createElement('figure');
  const img = new Image();
  img.src = src;
  img.width = 216;
  img.alt = caption;
  const figcaption = document.createElement('figcaption');
  figcaption.textContent = caption;
  figure.append(img, figcaption);
  li.appendChild(figure);
  return li;
}

$('quit').onclick = async () => {
  try { await api('/api/quit'); } catch (e) { /* the server is gone either way */ }
  say('Closed. You can close this tab.');
};
