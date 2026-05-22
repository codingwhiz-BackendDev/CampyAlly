/* ============================================================
   CAMPEASE — Civic Operations Platform
   JavaScript: interactions, charts, map, counters
   ============================================================ */

'use strict';

/* ---------- NAV SCROLL ---------- */
(function () {
  const nav = document.getElementById('siteNav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 10);
  }, { passive: true });
})();

/* ---------- HAMBURGER ---------- */
(function () {
  const btn = document.getElementById('hamburgerBtn');
  const linksWrap = document.querySelector('.nav-links-wrap');
  if (!btn || !linksWrap) return;
  btn.addEventListener('click', () => {
    const open = linksWrap.classList.toggle('mobile-open');
    btn.setAttribute('aria-expanded', open);
  });
})();

/* ---------- SCROLL REVEAL ---------- */
(function () {
  const els = document.querySelectorAll('.reveal');
  if (!els.length) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
  }, { threshold: 0.1 });
  els.forEach(el => obs.observe(el));
})();

/* ---------- ADMIN CLOCK ---------- */
(function () {
  const el = document.getElementById('adminClock');
  if (!el) return;
  const tick = () => {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' WAT';
  };
  tick();
  setInterval(tick, 1000);
})();

/* ---------- COUNT-UP ---------- */
function countUp(el) {
  const target = parseFloat(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
  const dur = 1600;
  const start = performance.now();
  const from = parseFloat(el.dataset.from || '0');
  function frame(now) {
    const p = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = from + (target - from) * ease;
    el.textContent = (decimals ? val.toFixed(decimals) : Math.round(val)).toLocaleString() + suffix;
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

(function () {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting && e.target.dataset.count !== undefined) {
        countUp(e.target);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });
  document.querySelectorAll('[data-count]').forEach(el => obs.observe(el));
})();

/* ---------- PROGRESS BARS ---------- */
(function () {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const fill = e.target;
        const w = fill.dataset.width;
        if (w) { setTimeout(() => { fill.style.width = w + '%'; }, 100); }
        obs.unobserve(fill);
      }
    });
  }, { threshold: 0.4 });
  document.querySelectorAll('[data-width]').forEach(el => obs.observe(el));
})();

/* ---------- MINI MAP (hero) ---------- */
(function () {
  const canvas = document.getElementById('miniMap');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 140;
    draw();
  }

  function draw() {
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background — light map-style
    ctx.fillStyle = '#f0f4f0';
    ctx.fillRect(0, 0, W, H);

    // Grid lines (road grid)
    ctx.strokeStyle = '#dde8dd';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 28) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 28) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    // Roads
    const roads = [
      { from: [0, H * 0.5], to: [W, H * 0.5], w: 5 },
      { from: [W * 0.5, 0], to: [W * 0.5, H], w: 5 },
      { from: [0, H * 0.25], to: [W, H * 0.25], w: 3 },
      { from: [0, H * 0.75], to: [W, H * 0.75], w: 3 },
      { from: [W * 0.3, 0], to: [W * 0.3, H], w: 3 },
      { from: [W * 0.7, 0], to: [W * 0.7, H], w: 3 },
    ];
    roads.forEach(r => {
      ctx.strokeStyle = '#c5d8c5';
      ctx.lineWidth = r.w;
      ctx.beginPath();
      ctx.moveTo(r.from[0], r.from[1]);
      ctx.lineTo(r.to[0], r.to[1]);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.6)';
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 5]);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Zone blocks
    const zones = [
      { x: 0.08, y: 0.05, w: 0.18, h: 0.18, color: 'rgba(45,147,73,0.12)', border: 'rgba(45,147,73,0.4)', label: 'P1' },
      { x: 0.72, y: 0.05, w: 0.2, h: 0.18, color: 'rgba(45,147,73,0.12)', border: 'rgba(45,147,73,0.4)', label: 'P2' },
      { x: 0.36, y: 0.32, w: 0.28, h: 0.36, color: 'rgba(45,147,73,0.08)', border: 'rgba(45,147,73,0.35)', label: 'ARENA' },
      { x: 0.08, y: 0.78, w: 0.18, h: 0.18, color: 'rgba(45,147,73,0.12)', border: 'rgba(45,147,73,0.4)', label: 'P3' },
      { x: 0.74, y: 0.78, w: 0.18, h: 0.18, color: 'rgba(45,147,73,0.12)', border: 'rgba(45,147,73,0.4)', label: 'P4' },
    ];
    zones.forEach(z => {
      ctx.fillStyle = z.color;
      ctx.fillRect(z.x * W, z.y * H, z.w * W, z.h * H);
      ctx.strokeStyle = z.border;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(z.x * W, z.y * H, z.w * W, z.h * H);
      ctx.fillStyle = 'rgba(45,147,73,0.7)';
      ctx.font = `bold ${W < 300 ? 7 : 8}px 'DM Sans', sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(z.label, (z.x + z.w / 2) * W, (z.y + z.h / 2) * H);
    });
    ctx.textBaseline = 'alphabetic';

    // Markers
    const markers = [
      { x: 0.5, y: 0.5, color: '#2d9349', icon: '●' },
      { x: 0.28, y: 0.35, color: '#dc2626', icon: '⚠' },
      { x: 0.72, y: 0.65, color: '#d97706', icon: '◆' },
    ];
    markers.forEach(m => {
      ctx.beginPath();
      ctx.arc(m.x * W, m.y * H, 7, 0, Math.PI * 2);
      ctx.fillStyle = 'white';
      ctx.fill();
      ctx.strokeStyle = m.color;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = m.color;
      ctx.font = `9px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(m.icon === '●' ? '' : m.icon, m.x * W, m.y * H);
      ctx.textBaseline = 'alphabetic';
    });
  }

  resize();
  const ro = new ResizeObserver(() => resize());
  ro.observe(canvas);
})();

/* ---------- MAIN CITY MAP ---------- */
(function () {
  const canvas = document.getElementById('mainMap');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let animId;

  function resize() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 420;
  }
  resize();

  const zones = [
    { id: 'P-NORTH', x: 0.05, y: 0.04, w: 0.2, h: 0.18, label: 'Parking North', color: '#2d9349', fill: 'rgba(45,147,73,0.1)', border: 'rgba(45,147,73,0.5)' },
    { id: 'P-SOUTH', x: 0.75, y: 0.78, w: 0.2, h: 0.18, label: 'Parking South', color: '#2d9349', fill: 'rgba(45,147,73,0.1)', border: 'rgba(45,147,73,0.5)' },
    { id: 'ARENA',   x: 0.32, y: 0.3,  w: 0.36, h: 0.4,  label: 'Main Arena', color: '#1d4ed8', fill: 'rgba(29,78,216,0.06)', border: 'rgba(29,78,216,0.3)' },
    { id: 'GATE-A',  x: 0.05, y: 0.78, w: 0.2, h: 0.18,  label: 'Gate A Zone', color: '#d97706', fill: 'rgba(217,119,6,0.08)', border: 'rgba(217,119,6,0.4)' },
    { id: 'GATE-B',  x: 0.75, y: 0.04, w: 0.2, h: 0.18,  label: 'Gate B Zone', color: '#d97706', fill: 'rgba(217,119,6,0.08)', border: 'rgba(217,119,6,0.4)' },
  ];

  const roads = [
    { pts: [[0, 0.5], [1, 0.5]], w: 8 },
    { pts: [[0.5, 0], [0.5, 1]], w: 8 },
    { pts: [[0, 0.23], [1, 0.23]], w: 5 },
    { pts: [[0, 0.77], [1, 0.77]], w: 5 },
    { pts: [[0.25, 0], [0.25, 1]], w: 5 },
    { pts: [[0.75, 0], [0.75, 1]], w: 5 },
  ];

  const markers = [
    { x: 0.17, y: 0.55, type: 'sos',    label: 'SOS Active' },
    { x: 0.6,  y: 0.25, type: 'lost',   label: 'Lost Person' },
    { x: 0.5,  y: 0.5,  type: 'crowd',  label: 'High Density' },
  ];

  const routeDots = [
    { road: 0, t: 0.05, speed: 0.0015, color: '#2d9349' },
    { road: 1, t: 0.6,  speed: 0.0012, color: '#2d9349' },
    { road: 2, t: 0.3,  speed: 0.001,  color: '#2d9349' },
  ];

  function getRoadPt(road, t) {
    const W = canvas.width, H = canvas.height;
    const p = roads[road].pts;
    const x = p[0][0] + (p[1][0] - p[0][0]) * t;
    const y = p[0][1] + (p[1][1] - p[0][1]) * t;
    return [x * W, y * H];
  }

  let frame = 0;
  function drawMap() {
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#f4f7f4';
    ctx.fillRect(0, 0, W, H);

    // Fine grid
    ctx.strokeStyle = '#e2eae2';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    // Roads
    roads.forEach(r => {
      ctx.strokeStyle = '#c8d8c8';
      ctx.lineWidth = r.w;
      ctx.beginPath();
      ctx.moveTo(r.pts[0][0] * W, r.pts[0][1] * H);
      ctx.lineTo(r.pts[1][0] * W, r.pts[1][1] * H);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(255,255,255,0.65)';
      ctx.lineWidth = 1;
      ctx.setLineDash([8, 7]);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Zones
    zones.forEach(z => {
      ctx.fillStyle = z.fill;
      ctx.fillRect(z.x * W, z.y * H, z.w * W, z.h * H);
      ctx.strokeStyle = z.border;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(z.x * W, z.y * H, z.w * W, z.h * H);
      ctx.fillStyle = z.color;
      ctx.font = `bold ${W < 500 ? 9 : 11}px 'DM Sans', sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(z.label, (z.x + z.w / 2) * W, (z.y + z.h / 2) * H);
      ctx.textBaseline = 'alphabetic';
    });

    // Markers
    markers.forEach(m => {
      const x = m.x * W, y = m.y * H;
      const pulse = frame % 60 < 30 ? frame % 30 : 30 - frame % 30;
      const alpha = 0.15 + (pulse / 30) * 0.15;
      const r = 14 + (pulse / 30) * 8;
      const color = m.type === 'sos' ? '#dc2626' : m.type === 'lost' ? '#1d4ed8' : '#d97706';

      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = color.replace(')', `,${alpha})`).replace('rgb', 'rgba').replace('#dc2626', `rgba(220,38,38,${alpha})`).replace('#1d4ed8', `rgba(29,78,216,${alpha})`).replace('#d97706', `rgba(217,119,6,${alpha})`);
      ctx.fill();

      ctx.beginPath();
      ctx.arc(x, y, 10, 0, Math.PI * 2);
      ctx.fillStyle = 'white';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();

      const icon = m.type === 'sos' ? '!' : m.type === 'lost' ? '?' : '▲';
      ctx.fillStyle = color;
      ctx.font = `bold ${W < 500 ? 9 : 11}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(icon, x, y);
      ctx.textBaseline = 'alphabetic';

      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.font = `${W < 500 ? 8 : 10}px 'DM Sans', sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(m.label, x, y + 22);
    });

    // Route dots
    routeDots.forEach(d => {
      d.t = (d.t + d.speed) % 1;
      const [rx, ry] = getRoadPt(d.road, d.t);
      ctx.beginPath();
      ctx.arc(rx, ry, 4, 0, Math.PI * 2);
      ctx.fillStyle = d.color;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(rx, ry, 7, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(45,147,73,0.2)';
      ctx.fill();
    });

    // Scale bar
    ctx.fillStyle = 'white';
    ctx.fillRect(W - 90, H - 28, 80, 18);
    ctx.strokeStyle = '#aab8aa';
    ctx.lineWidth = 1;
    ctx.strokeRect(W - 90, H - 28, 80, 18);
    ctx.fillStyle = '#4b5563';
    ctx.font = '9px DM Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText('0        500m', W - 50, H - 15);

    frame++;
    animId = requestAnimationFrame(drawMap);
  }
  drawMap();

  const ro = new ResizeObserver(() => { cancelAnimationFrame(animId); resize(); drawMap(); });
  ro.observe(canvas);
})();

/* ---------- ADMIN CHARTS ---------- */
(function () {
  // Crowd density line chart
  const cc = document.getElementById('adminChartCrowd');
  if (cc) {
    const ctx2 = cc.getContext('2d');
    const data = [42, 55, 68, 79, 83, 77, 71, 74];
    const labels = ['08h', '10h', '12h', '14h', '16h', '17h', '18h', 'NOW'];

    function drawCrowd() {
      const W = cc.width = cc.offsetWidth, H = 80;
      cc.height = H;
      ctx2.clearRect(0, 0, W, H);
      const pad = { l: 14, r: 10, t: 8, b: 18 };
      const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;

      // Grid
      ctx2.strokeStyle = '#f3f4f6';
      ctx2.lineWidth = 1;
      for (let i = 0; i <= 3; i++) {
        const y = pad.t + (ch / 3) * i;
        ctx2.beginPath(); ctx2.moveTo(pad.l, y); ctx2.lineTo(pad.l + cw, y); ctx2.stroke();
      }

      // Area
      const grd = ctx2.createLinearGradient(0, pad.t, 0, pad.t + ch);
      grd.addColorStop(0, 'rgba(45,147,73,0.18)');
      grd.addColorStop(1, 'rgba(45,147,73,0.01)');
      ctx2.beginPath();
      data.forEach((v, i) => {
        const x = pad.l + (i / (data.length - 1)) * cw;
        const y = pad.t + (1 - v / 100) * ch;
        i === 0 ? ctx2.moveTo(x, y) : ctx2.lineTo(x, y);
      });
      ctx2.lineTo(pad.l + cw, pad.t + ch);
      ctx2.lineTo(pad.l, pad.t + ch);
      ctx2.closePath();
      ctx2.fillStyle = grd;
      ctx2.fill();

      // Line
      ctx2.beginPath();
      data.forEach((v, i) => {
        const x = pad.l + (i / (data.length - 1)) * cw;
        const y = pad.t + (1 - v / 100) * ch;
        i === 0 ? ctx2.moveTo(x, y) : ctx2.lineTo(x, y);
      });
      ctx2.strokeStyle = '#2d9349';
      ctx2.lineWidth = 2;
      ctx2.stroke();

      // Labels
      ctx2.fillStyle = '#9ca3af';
      ctx2.font = '8px DM Mono, monospace';
      ctx2.textAlign = 'center';
      labels.forEach((l, i) => {
        const x = pad.l + (i / (data.length - 1)) * cw;
        ctx2.fillText(l, x, H - 3);
      });
    }
    drawCrowd();
    window.addEventListener('resize', drawCrowd);
  }

  // Parking bar chart
  const pc = document.getElementById('adminChartParking');
  if (pc) {
    const ctx3 = pc.getContext('2d');
    const zones = ['N', 'S', 'E', 'W', 'C1', 'C2'];
    const vals = [78, 91, 45, 62, 38, 55];

    function drawParking() {
      const W = pc.width = pc.offsetWidth, H = 80;
      pc.height = H;
      ctx3.clearRect(0, 0, W, H);
      const pad = { l: 10, r: 10, t: 10, b: 18 };
      const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;
      const bw = (cw / vals.length) * 0.55;
      const gap = (cw / vals.length) * 0.45;

      vals.forEach((v, i) => {
        const x = pad.l + i * (cw / vals.length) + gap / 2;
        const bh = (v / 100) * ch;
        const y = pad.t + ch - bh;
        const color = v >= 80 ? '#dc2626' : v >= 60 ? '#d97706' : '#2d9349';
        ctx3.fillStyle = color;
        ctx3.globalAlpha = 0.85;
        ctx3.fillRect(x, y, bw, bh);
        ctx3.globalAlpha = 1;
        ctx3.fillStyle = '#6b7280';
        ctx3.font = '8px DM Mono, monospace';
        ctx3.textAlign = 'center';
        ctx3.fillText(zones[i], x + bw / 2, H - 3);
        ctx3.fillStyle = color;
        ctx3.fillText(v + '%', x + bw / 2, y - 2);
      });
    }
    drawParking();
    window.addEventListener('resize', drawParking);
  }
})();

/* ---------- LIVE METRIC FLUCTUATION (subtle) ---------- */
(function () {
  const updates = [
    { id: 'liveParking', base: 847, variance: 15, suffix: '' },
    { id: 'liveCrowd',   base: 74,  variance: 4,  suffix: '%' },
    { id: 'liveAlerts',  base: 3,   variance: 1,  suffix: '' },
    { id: 'liveTraffic', base: 62,  variance: 8,  suffix: '' },
  ];
  updates.forEach(u => {
    setInterval(() => {
      const el = document.getElementById(u.id);
      if (el) {
        const val = u.base + Math.floor((Math.random() - 0.5) * 2 * u.variance);
        el.textContent = Math.max(0, val) + u.suffix;
      }
    }, 4000);
  });
})();

/* ---------- SMOOTH SCROLL FOR NAV LINKS ---------- */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});