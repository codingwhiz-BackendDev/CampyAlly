/* =============================================================================
   parking_dashboard.js
   Handles:
     1. Live polling — refreshes zone cards every 5 seconds
     2. Geofence nudge — checks user GPS against zone coords, shows banner
     3. Leaflet maps — renders a small map per zone with a marker
   ============================================================================= */

'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// 1. LIVE POLLING
// ─────────────────────────────────────────────────────────────────────────────

function timeSince(isoString) {
    const delta = Math.floor((Date.now() - new Date(isoString)) / 1000);
    if (delta < 5)  return 'Just now';
    if (delta < 60) return delta + 's ago';
    return Math.floor(delta / 60) + 'm ago';
}

async function pollDashboard() {
    try {
        const res = await fetch('/parking/api/status/');
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();

        // Update total available
        const totalAvail = data.zones.reduce((sum, z) => sum + z.available, 0);
        const totalEl = document.getElementById('total-available');
        if (totalEl) totalEl.textContent = totalAvail;

        // Update each zone card
        data.zones.forEach(zone => {
            const availEl = document.getElementById('zone-' + zone.id + '-available');
            const occEl   = document.getElementById('zone-' + zone.id + '-occupied');
            const totEl   = document.getElementById('zone-' + zone.id + '-total');
            const barEl   = document.getElementById('zone-' + zone.id + '-bar');
            const cardEl  = document.querySelector('[data-zone-id="' + zone.id + '"]');

            if (availEl) availEl.textContent = zone.available;
            if (occEl)   occEl.textContent   = zone.occupied;
            if (totEl)   totEl.textContent   = zone.total;

            if (barEl) {
                barEl.style.width = Math.min(zone.percent, 100) + '%';
                barEl.className   = 'progress-fill status-' + zone.status;
            }

            if (cardEl) {
                // Update zone card border / badge
                cardEl.className = 'zone-card status-' + zone.status;
                const badge = cardEl.querySelector('.zone-badge');
                if (badge) {
                    badge.className   = 'zone-badge status-' + zone.status;
                    badge.textContent = zone.status.charAt(0).toUpperCase() + zone.status.slice(1);
                }
            }
        });

        // Update poll indicator
        const pollEl = document.getElementById('poll-status');
        if (pollEl) {
            pollEl.innerHTML = '<span class="status-dot"></span><span>Live · ' + timeSince(data.timestamp) + '</span>';
        }

    } catch (err) {
        const pollEl = document.getElementById('poll-status');
        if (pollEl) pollEl.innerHTML = '<span style="color:#e53e3e">⚠ Connection issue</span>';
    }
}

// Start polling
pollDashboard();
setInterval(pollDashboard, 5000);


// ─────────────────────────────────────────────────────────────────────────────
// 2. GEOFENCE NUDGE
// ─────────────────────────────────────────────────────────────────────────────

const GEOFENCE_RADIUS_METRES = 150;   // how close the user must be to trigger nudge
let nudgeDismissed = false;

/**
 * Haversine formula — returns distance in metres between two lat/lng points.
 */
function haversineMetres(lat1, lng1, lat2, lng2) {
    const R    = 6371000; // Earth radius in metres
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a    = Math.sin(dLat / 2) * Math.sin(dLat / 2)
               + Math.cos(lat1 * Math.PI / 180)
               * Math.cos(lat2 * Math.PI / 180)
               * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function showNudge(zone) {
    const nudge   = document.getElementById('geo-nudge');
    const title   = document.getElementById('nudge-title');
    const sub     = document.getElementById('nudge-sub');
    const btnYes  = document.getElementById('nudge-btn-yes');

    if (!nudge) return;

    title.textContent = 'You appear to be near ' + zone.name;
    sub.textContent   = zone.available + ' spot' + (zone.available !== 1 ? 's' : '') + ' available · Tap to check in';
    btnYes.href       = zone.url;
    nudge.style.display = 'block';
}

function dismissNudge() {
    nudgeDismissed = true;
    const nudge = document.getElementById('geo-nudge');
    if (nudge) nudge.style.display = 'none';
}

function checkGeofence(position) {
    if (nudgeDismissed) return;

    const userLat = position.coords.latitude;
    const userLng = position.coords.longitude;

    // Find the closest zone that has real coordinates and is not full
    let closest     = null;
    let closestDist = Infinity;

    ZONES_GEO.forEach(zone => {
        if (!zone.has_coords) return;          // skip placeholder 0,0 zones
        if (zone.status === 'full') return;    // no point nudging to a full zone
        if (zone.available <= 0) return;

        const dist = haversineMetres(userLat, userLng, zone.lat, zone.lng);
        if (dist < GEOFENCE_RADIUS_METRES && dist < closestDist) {
            closest     = zone;
            closestDist = dist;
        }
    });

    if (closest) {
        showNudge(closest);
    }
}

function initGeofence() {
    // Only ask for location if there is at least one zone with real coordinates
    const hasRealCoords = ZONES_GEO.some(z => z.has_coords);
    if (!hasRealCoords) return;

    if (!navigator.geolocation) return;

    // Ask once — we don't need continuous tracking
    navigator.geolocation.getCurrentPosition(
        checkGeofence,
        function(err) {
            // User denied or unavailable — silently ignore, no nudge shown
            console.log('Geolocation unavailable:', err.message);
        },
        { timeout: 8000, maximumAge: 30000 }
    );
}

// Kick off geofence check after a short delay
// (gives the page time to render before the browser shows the location prompt)
setTimeout(initGeofence, 1500);


// ─────────────────────────────────────────────────────────────────────────────
// 3. LEAFLET MAPS — one small map per zone card
// ─────────────────────────────────────────────────────────────────────────────

function initMaps() {
    // Find all zone map containers
    const mapDivs = document.querySelectorAll('.zone-map');

    mapDivs.forEach(function(div) {
        const lat  = parseFloat(div.dataset.lat);
        const lng  = parseFloat(div.dataset.lng);
        const name = div.dataset.name || 'Parking Zone';

        if (!lat || !lng) return;  // skip if somehow still 0,0

        const map = L.map(div, {
            center: [lat, lng],
            zoom: 16,
            zoomControl: false,       // keep it clean — no zoom buttons
            scrollWheelZoom: false,   // prevent accidental scroll-zoom
            dragging: false,          // static preview, not interactive
            doubleClickZoom: false,
            attributionControl: false,
        });

        // Dark-styled tile layer from CartoDB
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
        }).addTo(map);

        // Custom parking marker
        const icon = L.divIcon({
            className: '',
            html: '<div style="'
                + 'background:#63b3ed;'
                + 'width:32px;height:32px;'
                + 'border-radius:50% 50% 50% 0;'
                + 'transform:rotate(-45deg);'
                + 'border:3px solid #fff;'
                + 'box-shadow:0 2px 8px rgba(0,0,0,0.4);'
                + '"></div>',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
        });

        L.marker([lat, lng], { icon: icon })
            .addTo(map)
            .bindPopup('<strong>' + name + '</strong><br>Parking Zone', { closeButton: false });

        // Draw a subtle circle to show the 150m geofence radius
        L.circle([lat, lng], {
            radius: 150,
            color: '#63b3ed',
            fillColor: '#63b3ed',
            fillOpacity: 0.08,
            weight: 1,
        }).addTo(map);
    });
}

// Wait for Leaflet to be ready
if (typeof L !== 'undefined') {
    initMaps();
} else {
    window.addEventListener('load', initMaps);
}