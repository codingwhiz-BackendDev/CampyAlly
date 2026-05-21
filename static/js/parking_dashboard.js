// ============================================================
// PARKING DASHBOARD JAVASCRIPT
// Handles real-time polling and UI updates
// ============================================================

const STATUS_COLORS = {
    open: 'linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%)',
    filling: 'linear-gradient(90deg, var(--orange) 0%, #fb923c 100%)',
    full: 'linear-gradient(90deg, var(--red) 0%, #f87171 100%)',
    closed: 'linear-gradient(90deg, var(--text-secondary) 0%, #94a3b8 100%)',
};

function timeSince(isoString) {
    const delta = Math.floor((Date.now() - new Date(isoString)) / 1000);
    if (delta < 5) return 'Just now';
    if (delta < 60) return `${delta}s ago`;
    if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
    return `${Math.floor(delta / 3600)}h ago`;
}

async function pollStatus() {
    try {
        const res = await fetch('/parking/api/status/');
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();

        // Update total available
        const totalAvailable = data.zones.reduce((sum, zone) => sum + zone.available, 0);
        const totalAvailableEl = document.getElementById('total-available');
        if (totalAvailableEl) {
            totalAvailableEl.textContent = totalAvailable;
        }

        // Update each zone card
        data.zones.forEach(zone => {
            const availableEl = document.getElementById(`zone-${zone.id}-available`);
            const occupiedEl = document.getElementById(`zone-${zone.id}-occupied`);
            const totalEl = document.getElementById(`zone-${zone.id}-total`);
            const barEl = document.getElementById(`zone-${zone.id}-bar`);
            const cardEl = document.querySelector(`[data-zone-id="${zone.id}"]`);

            if (availableEl) availableEl.textContent = zone.available;
            if (occupiedEl) occupiedEl.textContent = zone.occupied;
            if (totalEl) totalEl.textContent = zone.total;

            if (barEl) {
                barEl.style.width = Math.min(zone.percent, 100) + '%';
                barEl.className = `progress-fill status-${zone.status}`;
            }

            if (cardEl) {
                cardEl.className = `zone-card status-${zone.status}`;
                const badgeEl = cardEl.querySelector('.zone-badge');
                if (badgeEl) {
                    badgeEl.className = `zone-badge status-${zone.status}`;
                    badgeEl.textContent = zone.status.charAt(0).toUpperCase() + zone.status.slice(1);
                }
            }
        });

        // Show/hide active banner
        if (data.active_slot) {
            const bannerEl = document.getElementById('active-banner');
            if (!bannerEl) {
                // Reload page once so server renders the banner properly
                location.reload();
            }
        }

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
pollStatus();

// Poll every 5 seconds
setInterval(pollStatus, 5000);
