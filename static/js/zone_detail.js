// ============================================================
// ZONE DETAIL JAVASCRIPT
// Handles real-time polling and UI updates for zone detail page
// ============================================================

const ZONE_ID = {{ zone.id }};

function timeSince(isoString) {
    const delta = Math.floor((Date.now() - new Date(isoString)) / 1000);
    if (delta < 5) return 'Just now';
    if (delta < 60) return `${delta}s ago`;
    if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
    return `${Math.floor(delta / 3600)}h ago`;
}

async function pollZoneStatus() {
    try {
        const res = await fetch(`/parking/api/zone/${ZONE_ID}/`);
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();

        // Update zone stats
        const availableEl = document.getElementById('zone-available');
        const occupiedEl = document.getElementById('zone-occupied');
        const totalEl = document.getElementById('zone-total');

        if (availableEl) availableEl.textContent = data.available;
        if (occupiedEl) occupiedEl.textContent = data.occupied;
        if (totalEl) totalEl.textContent = data.total;

        // Update zone badge
        const zoneBadgeEl = document.querySelector('.zone-badge');
        if (zoneBadgeEl) {
            zoneBadgeEl.className = `zone-badge status-${data.status}`;
            zoneBadgeEl.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        }

        // Update each slot card
        data.slots.forEach(slot => {
            const slotCard = document.querySelector(`[data-slot-id="${slot.id}"]`);
            if (!slotCard) return;

            // Update card status class
            slotCard.className = `slot-card status-${slot.status}`;

            // Update slot status badge
            const statusBadge = slotCard.querySelector('.slot-status');
            if (statusBadge) {
                statusBadge.className = `slot-status ${slot.status}`;
                statusBadge.textContent = slot.status.charAt(0).toUpperCase() + slot.status.slice(1);
            }

            // Update slot icon
            const slotIcon = slotCard.querySelector('.slot-icon i');
            if (slotIcon) {
                if (slot.status === 'occupied') {
                    slotIcon.className = 'fa-solid fa-car';
                } else if (slot.status === 'blocked') {
                    slotIcon.className = 'fa-solid fa-ban';
                } else {
                    slotIcon.className = 'fa-solid fa-square-parking';
                }
            }

            // Update detected vehicles count
            const slotLabel = slotCard.querySelector('.slot-label');
            if (slotLabel) {
                slotLabel.textContent = `Detected: ${slot.detected_vehicles} vehicle${slot.detected_vehicles !== 1 ? 's' : ''}`;
            }

            // Update last scan time
            const slotMeta = slotCard.querySelector('.slot-meta');
            if (slotMeta && slot.last_detection_at) {
                slotMeta.textContent = `Last scan: ${timeSince(slot.last_detection_at)}`;
            }
        });

        // Update poll status
        const pollStatusEl = document.getElementById('poll-status');
        if (pollStatusEl) {
            const statusText = pollStatusEl.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = 'Live · ' + timeSince(data.timestamp);
            }
        }

    } catch (err) {
        console.error('Polling error:', err);
        const pollStatusEl = document.getElementById('poll-status');
        if (pollStatusEl) {
            const statusText = pollStatusEl.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = '⚠ Connection issue — retrying…';
            }
        }
    }
}

// Initial poll
pollZoneStatus();

// Poll every 4 seconds
setInterval(pollZoneStatus, 4000);
