/* ============================================================
   CAMPEASE — World-Class Civic Platform JS
   RCCG Redemption City · Lat 6.4531°N · Lng 3.3958°E
   ============================================================ */
'use strict';

/* ── NAV STATE ─────────────────────────────────────────── */
(function () {
  const nav = document.querySelector('.site-nav');
  if (!nav) return;
  function update() {
    if (window.scrollY > 60) {
      nav.classList.add('solid');
      nav.classList.remove('hero-nav');
    } else {
      nav.classList.remove('solid');
      nav.classList.add('hero-nav');
    }
  }
  update();
  window.addEventListener('scroll', update, { passive: true });
})();

/* ── HAMBURGER ─────────────────────────────────────────── */
(function () {
  const btn = document.getElementById('hamburgerBtn');
  const wrap = document.querySelector('.nav-links');
  if (!btn || !wrap) return;
  btn.addEventListener('click', () => {
    const open = wrap.classList.toggle('mobile-open');
    btn.setAttribute('aria-expanded', open);
  });
})();

/* ── SMOOTH SCROLL ─────────────────────────────────────── */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', function (e) {
    const t = document.querySelector(this.getAttribute('href'));
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  });
});

/* ── SCROLL REVEAL ─────────────────────────────────────── */
(function () {
  const els = document.querySelectorAll('.reveal,.reveal-l,.reveal-r');
  if (!els.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.1 });
  els.forEach(el => io.observe(el));
})();

/* ── HERO CYCLING PHRASES ──────────────────────────────── */
(function () {
  const wrap = document.getElementById('heroPhraseWrap');
  if (!wrap) return;
  const phrases = [
    'Smart crowd & traffic coordination for large gatherings.',
    'Real-time parking guidance across all 12 zones.',
    'Emergency SOS dispatch in under 90 seconds.',
    'Lost person recovery powered by RFID & crowd-data.',
    'Keeping Redemption City safe, organised & peaceful.',
  ];
  let idx = 0;
  function show() {
    wrap.innerHTML = '';
    const span = document.createElement('span');
    span.className = 'hero-phrase';
    span.textContent = phrases[idx];
    wrap.appendChild(span);
    idx = (idx + 1) % phrases.length;
  }
  show();
  setInterval(show, 4200);
})();

/* ── ADMIN CLOCK ────────────────────────────────────────── */
(function () {
  const el = document.getElementById('adminClock');
  if (!el) return;
  const tick = () => {
    el.textContent = new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }) + ' WAT';
  };
  tick(); setInterval(tick, 1000);
})();

/* ── COUNT-UP ───────────────────────────────────────────── */
function countUp(el) {
  const target = parseFloat(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const from   = parseFloat(el.dataset.from || 0);
  const dur    = 1800;
  const t0     = performance.now();
  function frame(now) {
    const p = Math.min((now - t0) / dur, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val  = from + (target - from) * ease;
    el.textContent = (Number.isInteger(target) ? Math.round(val) : val.toFixed(1)).toLocaleString() + suffix;
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
(function () {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && e.target.dataset.count != null) {
        countUp(e.target); io.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });
  document.querySelectorAll('[data-count]').forEach(el => io.observe(el));
})();

/* ── PROGRESS BAR ANIMATE ──────────────────────────────── */
(function () {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const w = e.target.dataset.width;
        if (w) setTimeout(() => { e.target.style.transform = `scaleX(${parseFloat(w)/100})`; }, 120);
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.4 });
  document.querySelectorAll('.mc-bar-fill').forEach(el => io.observe(el));
})();

/* ── LIVE METRIC FLUCTUATION ────────────────────────────── */
(function () {
  const items = [
    { id:'liveP', base:847, v:18, sfx:'' },
    { id:'liveC', base:74,  v:4,  sfx:'%' },
    { id:'liveE', base:3,   v:1,  sfx:'' },
    { id:'liveT', base:62,  v:7,  sfx:'' },
  ];
  items.forEach(u => setInterval(() => {
    const el = document.getElementById(u.id);
    if (el) el.textContent = Math.max(0, u.base + Math.round((Math.random()-.5)*2*u.v)) + u.sfx;
  }, 5000));
})();

/* ── RCCG REDEMPTION CITY MAP ────────────────────────────
   Real coordinates: 6.4531°N, 3.3958°E
   Canvas renders a simplified top-down map representation
   ─────────────────────────────────────────────────────── */
(function () {
  const canvas = document.getElementById('mainMap');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let animId, frame = 0;

  /* ── Road network (relative coords, anchored to campus layout) */
  /* RCCG camp has a roughly grid-like internal road system with a
     central Redemption Road axis running N-S and lateral connectors */
  const roads = [
    // Main Redemption Road (N-S spine)
    { pts:[[.5,.02],[.5,.98]], w:10, name:'Redemption Road' },
    // East-West main connector at mid
    { pts:[[.02,.5],[.98,.5]], w:8 },
    // Northern horizontal
    { pts:[[.1,.22],[.9,.22]], w:6 },
    // Southern horizontal
    { pts:[[.1,.78],[.9,.78]], w:6 },
    // Western vertical
    { pts:[[.22,.05],[.22,.95]], w:5 },
    // Eastern vertical
    { pts:[[.78,.05],[.78,.95]], w:5 },
    // Internal connectors
    { pts:[[.22,.22],[.5,.22]], w:4 },
    { pts:[[.5,.22],[.78,.22]], w:4 },
    { pts:[[.22,.78],[.5,.78]], w:4 },
    { pts:[[.5,.78],[.78,.78]], w:4 },
  ];

  /* ── Zone definitions (real-ish layout of RCCG camp zones) */
  const zones = [
    { x:.28, y:.08, w:.44, h:.12, label:'RCCG Prayer City',    fc:'rgba(39,135,61,.1)',  bc:'rgba(39,135,61,.5)',  tc:'#1e6b31' },
    { x:.06, y:.27, w:.14, h:.44, label:'Campground West',      fc:'rgba(26,79,168,.07)', bc:'rgba(26,79,168,.3)',  tc:'#1a4fa8' },
    { x:.8,  y:.27, w:.14, h:.44, label:'Campground East',      fc:'rgba(26,79,168,.07)', bc:'rgba(26,79,168,.3)',  tc:'#1a4fa8' },
    { x:.28, y:.28, w:.44, h:.44, label:'Main Auditorium',      fc:'rgba(39,135,61,.06)', bc:'rgba(39,135,61,.45)', tc:'#1e6b31' },
    { x:.06, y:.82, w:.14, h:.14, label:'P-West',               fc:'rgba(39,135,61,.12)', bc:'rgba(39,135,61,.5)',  tc:'#1e6b31' },
    { x:.8,  y:.82, w:.14, h:.14, label:'P-East',               fc:'rgba(39,135,61,.12)', bc:'rgba(39,135,61,.5)',  tc:'#1e6b31' },
    { x:.28, y:.82, w:.44, h:.14, label:'Parking South',        fc:'rgba(39,135,61,.1)',  bc:'rgba(39,135,61,.4)',  tc:'#1e6b31' },
    { x:.06, y:.06, w:.14, h:.14, label:'Gate A',               fc:'rgba(180,83,9,.1)',   bc:'rgba(180,83,9,.5)',   tc:'#b45309' },
    { x:.8,  y:.06, w:.14, h:.14, label:'Gate B',               fc:'rgba(180,83,9,.1)',   bc:'rgba(180,83,9,.5)',   tc:'#b45309' },
  ];

  /* ── Incident markers */
  const markers = [
    { rx:.38, ry:.42, type:'crowd', lbl:'High Crowd' },
    { rx:.2,  ry:.58, type:'sos',   lbl:'SOS Active' },
    { rx:.65, ry:.32, type:'lost',  lbl:'Lost Person' },
  ];
  const mColors = { crowd:'#b45309', sos:'#c0392b', lost:'#1a4fa8' };
  const mIcons  = { crowd:'▲', sos:'!', lost:'?' };

  /* ── Moving route vehicles */
  const vehicles = [
    { road:0, t:.1,  spd:.0014, c:'#27873d' },
    { road:1, t:.55, spd:.0011, c:'#27873d' },
    { road:2, t:.3,  spd:.0009, c:'#1a4fa8' },
  ];

  function resize() {
    canvas.width  = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 460;
  }
  resize();

  function getRoadPt(road, t) {
    const W = canvas.width, H = canvas.height;
    const p = roads[road].pts;
    return [
      (p[0][0] + (p[1][0]-p[0][0])*t)*W,
      (p[0][1] + (p[1][1]-p[0][1])*t)*H,
    ];
  }

  function draw() {
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0,0,W,H);

    /* Map background — warm green-tinted paper feel */
    ctx.fillStyle = '#eef5ee';
    ctx.fillRect(0,0,W,H);

    /* Subtle map grid */
    ctx.strokeStyle = '#dceadc';
    ctx.lineWidth = .8;
    for (let x=0;x<W;x+=36){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for (let y=0;y<H;y+=36){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}

    /* Roads */
    roads.forEach(r=>{
      const [x1,y1] = [r.pts[0][0]*W, r.pts[0][1]*H];
      const [x2,y2] = [r.pts[1][0]*W, r.pts[1][1]*H];
      /* Road bed */
      ctx.strokeStyle = '#c6d9c6';
      ctx.lineWidth = r.w + 4;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
      /* Road surface */
      ctx.strokeStyle = '#d8e8d8';
      ctx.lineWidth = r.w;
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
      /* Centre dashes */
      if (r.w >= 6) {
        ctx.strokeStyle = 'rgba(255,255,255,.7)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([10,9]);
        ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
        ctx.setLineDash([]);
      }
      /* Road name */
      if (r.name) {
        ctx.save();
        ctx.translate((x1+x2)/2,(y1+y2)/2);
        const angle = Math.atan2(y2-y1,x2-x1);
        ctx.rotate(angle);
        ctx.fillStyle = 'rgba(80,110,80,.55)';
        ctx.font = `${W<500?7:9}px 'DM Mono',monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(r.name, 0, -(r.w/2+6));
        ctx.restore();
      }
    });

    /* Zones */
    zones.forEach(z=>{
      const zx=z.x*W, zy=z.y*H, zw=z.w*W, zh=z.h*H;
      ctx.fillStyle = z.fc;
      roundRect(ctx, zx, zy, zw, zh, 6); ctx.fill();
      ctx.strokeStyle = z.bc; ctx.lineWidth = 1.5;
      roundRect(ctx, zx, zy, zw, zh, 6); ctx.stroke();
      ctx.fillStyle = z.tc;
      ctx.font = `bold ${W<500?7:Math.min(10,zw/z.label.length*1.2)}px 'DM Sans',sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(z.label, zx+zw/2, zy+zh/2);
    });

    /* Incident markers */
    markers.forEach(m=>{
      const mx=m.rx*W, my=m.ry*H;
      const pulse = (Math.sin(frame*.07)+1)/2;
      const pR = 14 + pulse*8;
      const col = mColors[m.type];
      const [cr,cg,cb] = hexToRGB(col);
      /* Pulse ring */
      ctx.beginPath(); ctx.arc(mx,my,pR,0,Math.PI*2);
      ctx.fillStyle = `rgba(${cr},${cg},${cb},${.08+pulse*.09})`;
      ctx.fill();
      /* White pin */
      ctx.beginPath(); ctx.arc(mx,my,10,0,Math.PI*2);
      ctx.fillStyle = 'white'; ctx.fill();
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.stroke();
      /* Icon */
      ctx.fillStyle = col;
      ctx.font = `bold ${W<500?9:11}px sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(mIcons[m.type], mx, my);
      /* Label */
      ctx.fillStyle = 'rgba(0,0,0,.6)';
      ctx.font = `${W<500?8:10}px 'DM Sans',sans-serif`;
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(m.lbl, mx, my+24);
    });

    /* Moving vehicles on roads */
    vehicles.forEach(v=>{
      v.t = (v.t+v.spd)%1;
      const [vx,vy] = getRoadPt(v.road, v.t);
      ctx.beginPath(); ctx.arc(vx,vy,4.5,0,Math.PI*2);
      ctx.fillStyle = v.c; ctx.fill();
      ctx.beginPath(); ctx.arc(vx,vy,8,0,Math.PI*2);
      const [vr,vg,vb] = hexToRGB(v.c);
      ctx.fillStyle = `rgba(${vr},${vg},${vb},.2)`; ctx.fill();
    });

    /* Compass rose (top-right) */
    drawCompass(ctx, W-38, 42, 22);

    /* Scale bar */
    ctx.fillStyle = 'rgba(255,255,255,.9)';
    ctx.strokeStyle = '#aabcaa'; ctx.lineWidth = 1;
    roundRect(ctx, W-92, H-30, 82, 20, 3); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#4a5e57';
    ctx.font = '8px DM Mono,monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('0     ~200m', W-51, H-20);

    /* Coordinates watermark */
    ctx.fillStyle = 'rgba(30,107,49,.35)';
    ctx.font = '8px DM Mono,monospace'; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    ctx.fillText('6.4531°N  3.3958°E', 10, H-10);

    frame++;
    animId = requestAnimationFrame(draw);
  }
  draw();

  const ro = new ResizeObserver(()=>{ cancelAnimationFrame(animId); resize(); draw(); });
  ro.observe(canvas);

  /* Helpers */
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x+r,y); ctx.lineTo(x+w-r,y);
    ctx.quadraticCurveTo(x+w,y,x+w,y+r);
    ctx.lineTo(x+w,y+h-r);
    ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    ctx.lineTo(x+r,y+h);
    ctx.quadraticCurveTo(x,y+h,x,y+h-r);
    ctx.lineTo(x,y+r);
    ctx.quadraticCurveTo(x,y,x+r,y);
    ctx.closePath();
  }
  function hexToRGB(hex) {
    const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
    return [r,g,b];
  }
  function drawCompass(ctx, cx, cy, r) {
    ctx.save();
    ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2);
    ctx.fillStyle='rgba(255,255,255,.85)'; ctx.fill();
    ctx.strokeStyle='#b8cac4'; ctx.lineWidth=1; ctx.stroke();
    /* N arrow */
    ctx.fillStyle='#c0392b';
    ctx.beginPath(); ctx.moveTo(cx,cy-r+4); ctx.lineTo(cx-4,cy+2); ctx.lineTo(cx+4,cy+2); ctx.closePath(); ctx.fill();
    /* S arrow */
    ctx.fillStyle='#8fa39b';
    ctx.beginPath(); ctx.moveTo(cx,cy+r-4); ctx.lineTo(cx-4,cy-2); ctx.lineTo(cx+4,cy-2); ctx.closePath(); ctx.fill();
    ctx.fillStyle='#1e6b31'; ctx.font='bold 9px DM Sans,sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText('N', cx, cy-r+12);
    ctx.restore();
  }
})();

/* ── HERO MINI MAP ─────────────────────────────────────── */
(function () {
  const canvas = document.getElementById('miniMap');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() { canvas.width=canvas.offsetWidth; canvas.height=canvas.offsetHeight||200; draw(); }

  function draw() {
    const W=canvas.width, H=canvas.height;
    ctx.clearRect(0,0,W,H);
    ctx.fillStyle='#eef5ee'; ctx.fillRect(0,0,W,H);
    ctx.strokeStyle='#dceadc'; ctx.lineWidth=.7;
    for(let x=0;x<W;x+=28){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for(let y=0;y<H;y+=28){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
    /* roads */
    [[0,H*.5,W,H*.5,6],[W*.5,0,W*.5,H,6],[0,H*.25,W,H*.25,3],[0,H*.75,W,H*.75,3],[W*.3,0,W*.3,H,3],[W*.7,0,W*.7,H,3]].forEach(r=>{
      ctx.strokeStyle='#cfdecf'; ctx.lineWidth=r[4]+3; ctx.lineCap='round';
      ctx.beginPath(); ctx.moveTo(r[0],r[1]); ctx.lineTo(r[2],r[3]); ctx.stroke();
      ctx.strokeStyle='#d8e8d8'; ctx.lineWidth=r[4];
      ctx.beginPath(); ctx.moveTo(r[0],r[1]); ctx.lineTo(r[2],r[3]); ctx.stroke();
    });
    /* zones */
    [
      [.08,.08,.18,.18,'rgba(39,135,61,.12)','rgba(39,135,61,.45)','P-A'],
      [.74,.08,.18,.18,'rgba(39,135,61,.12)','rgba(39,135,61,.45)','P-B'],
      [.3,.3,.4,.4,'rgba(39,135,61,.07)','rgba(39,135,61,.4)','ARENA'],
      [.08,.74,.18,.18,'rgba(39,135,61,.12)','rgba(39,135,61,.45)','P-C'],
      [.74,.74,.18,.18,'rgba(39,135,61,.12)','rgba(39,135,61,.45)','P-D'],
    ].forEach(z=>{
      ctx.fillStyle=z[4]; ctx.fillRect(z[0]*W,z[1]*H,z[2]*W,z[3]*H);
      ctx.strokeStyle=z[5]; ctx.lineWidth=1.2; ctx.strokeRect(z[0]*W,z[1]*H,z[2]*W,z[3]*H);
      ctx.fillStyle='rgba(30,107,49,.7)'; ctx.font=`bold ${W<280?6:8}px DM Sans,sans-serif`;
      ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(z[6],(z[0]+z[2]/2)*W,(z[1]+z[3]/2)*H);
    });
    /* markers */
    [[.5,.5,'#27873d'],[.28,.37,'#c0392b'],[.7,.63,'#b45309']].forEach(m=>{
      ctx.beginPath(); ctx.arc(m[0]*W,m[1]*H,6.5,0,Math.PI*2);
      ctx.fillStyle='white'; ctx.fill();
      ctx.strokeStyle=m[2]; ctx.lineWidth=2; ctx.stroke();
      ctx.beginPath(); ctx.arc(m[0]*W,m[1]*H,3,0,Math.PI*2);
      ctx.fillStyle=m[2]; ctx.fill();
    });
  }
  resize();
  new ResizeObserver(()=>resize()).observe(canvas);
})();

/* ── ADMIN CHARTS ───────────────────────────────────────── */
(function () {
  /* Crowd density line */
  const cc = document.getElementById('chCrowd');
  if (cc) {
    const ctx2=cc.getContext('2d');
    const data=[42,55,68,79,83,77,71,74];
    const labs=['08h','10h','12h','14h','16h','17h','18h','NOW'];
    function dCrowd(){
      const W=cc.width=cc.offsetWidth, H=82; cc.height=H;
      ctx2.clearRect(0,0,W,H);
      const p={l:12,r:8,t:8,b:18}, cw=W-p.l-p.r, ch=H-p.t-p.b;
      ctx2.strokeStyle='#f3f4f6'; ctx2.lineWidth=1;
      for(let i=0;i<=3;i++){const y=p.t+(ch/3)*i; ctx2.beginPath();ctx2.moveTo(p.l,y);ctx2.lineTo(p.l+cw,y);ctx2.stroke();}
      const g=ctx2.createLinearGradient(0,p.t,0,p.t+ch);
      g.addColorStop(0,'rgba(39,135,61,.2)'); g.addColorStop(1,'rgba(39,135,61,.01)');
      ctx2.beginPath();
      data.forEach((v,i)=>{ const x=p.l+(i/(data.length-1))*cw, y=p.t+(1-v/100)*ch; i?ctx2.lineTo(x,y):ctx2.moveTo(x,y); });
      ctx2.lineTo(p.l+cw,p.t+ch); ctx2.lineTo(p.l,p.t+ch); ctx2.closePath();
      ctx2.fillStyle=g; ctx2.fill();
      ctx2.beginPath();
      data.forEach((v,i)=>{ const x=p.l+(i/(data.length-1))*cw, y=p.t+(1-v/100)*ch; i?ctx2.lineTo(x,y):ctx2.moveTo(x,y); });
      ctx2.strokeStyle='#27873d'; ctx2.lineWidth=2; ctx2.stroke();
      data.forEach((v,i)=>{ const x=p.l+(i/(data.length-1))*cw, y=p.t+(1-v/100)*ch; ctx2.beginPath();ctx2.arc(x,y,2.5,0,Math.PI*2);ctx2.fillStyle='#27873d';ctx2.fill(); });
      ctx2.fillStyle='#9ca3af'; ctx2.font='8px DM Mono,monospace'; ctx2.textAlign='center';
      labs.forEach((l,i)=>{ ctx2.fillText(l, p.l+(i/(labs.length-1))*cw, H-3); });
    }
    dCrowd(); window.addEventListener('resize', dCrowd);
  }
  /* Parking bars */
  const pc = document.getElementById('chParking');
  if (pc) {
    const ctx3=pc.getContext('2d');
    const zones=['N','S','E','W','C1','C2'], vals=[78,91,45,62,38,55];
    function dPark(){
      const W=pc.width=pc.offsetWidth, H=82; pc.height=H;
      ctx3.clearRect(0,0,W,H);
      const p={l:8,r:8,t:10,b:18}, cw=W-p.l-p.r, ch=H-p.t-p.b;
      const bw=(cw/vals.length)*.54, gap=(cw/vals.length)*.46;
      vals.forEach((v,i)=>{
        const x=p.l+i*(cw/vals.length)+gap/2, bh=(v/100)*ch, y=p.t+ch-bh;
        const col=v>=80?'#c0392b':v>=60?'#b45309':'#27873d';
        ctx3.globalAlpha=.88; ctx3.fillStyle=col; ctx3.fillRect(x,y,bw,bh);
        ctx3.globalAlpha=1;
        ctx3.fillStyle='#6b7280'; ctx3.font='8px DM Mono,monospace'; ctx3.textAlign='center';
        ctx3.fillText(zones[i], x+bw/2, H-3);
        ctx3.fillStyle=col; ctx3.fillText(v+'%', x+bw/2, y-2);
      });
    }
    dPark(); window.addEventListener('resize', dPark);
  }
})();

/* ── VIDEO FALLBACK / CONTROL ───────────────────────────── */
(function () {
  const video = document.getElementById('heroVideo');
  if (!video) return;
  video.addEventListener('error', () => {
    const wrap = video.closest('.hero-video-wrap');
    if (wrap) wrap.style.background = 'linear-gradient(160deg, #062715 0%, #0d3d20 40%, #155228 100%)';
    video.style.display = 'none';
  });
  /* Mute toggle */
  const muteBtn = document.getElementById('muteBtn');
  if (muteBtn) {
    muteBtn.addEventListener('click', () => {
      video.muted = !video.muted;
      muteBtn.querySelector('i').className = video.muted ? 'fa-solid fa-volume-xmark' : 'fa-solid fa-volume-low';
    });
  }
})();