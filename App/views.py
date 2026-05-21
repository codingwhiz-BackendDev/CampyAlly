import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from .models import ParkingZone, ParkingSlot, CheckInSession


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SESSION_KEY = 'parking_session_token'   # key stored in Django session (browser cookie)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_token(request):
    """Every browser gets a unique token stored in Django's session."""
    if SESSION_KEY not in request.session:
        request.session[SESSION_KEY] = uuid.uuid4().hex
    return request.session[SESSION_KEY]


def _get_active_slot(request):
    """Return the slot this browser is currently parked in, or None."""
    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    return ParkingSlot.objects.filter(session_token=token, status='occupied').first()


def _release_expired_slots():
    """
    Auto-release any slots whose 24-hour window has passed.
    Called at the top of every page view so no background task is needed.
    """
    expired = ParkingSlot.objects.filter(
        status='occupied',
        auto_release_at__lt=timezone.now()
    )
    for slot in expired:
        slot.check_out()


# ─────────────────────────────────────────────────────────────────────────────
# Landing page  /
# ─────────────────────────────────────────────────────────────────────────────

def index(request):
    return render(request, 'index.html')


# ─────────────────────────────────────────────────────────────────────────────
# Parking dashboard  /parking/
# ─────────────────────────────────────────────────────────────────────────────

def parking_dashboard(request):
    _release_expired_slots()
    zones       = ParkingZone.objects.prefetch_related('slots').all()
    active_slot = _get_active_slot(request)

    return render(request, 'parking_dashboard.html', {
        'zones':       zones,
        'active_slot': active_slot,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Zone detail  /parking/zone/<id>/
# ─────────────────────────────────────────────────────────────────────────────

def zone_detail(request, zone_id):
    _release_expired_slots()
    zone        = get_object_or_404(ParkingZone, id=zone_id)
    slots       = zone.slots.all().order_by('slot_number')
    active_slot = _get_active_slot(request)

    return render(request, 'zone_detail.html', {
        'zone':        zone,
        'slots':       slots,
        'active_slot': active_slot,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Check-in  POST /parking/checkin/<slot_id>/
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def checkin(request, slot_id):
    token = _get_or_create_token(request)

    # Prevent double check-in from the same browser
    existing = _get_active_slot(request)
    if existing:
        messages.warning(
            request,
            f"You're already checked in to Slot {existing.slot_number} "
            f"in {existing.zone.name}. Check out first."
        )
        return redirect('zone_detail', zone_id=existing.zone.id)

    vehicle_plate = request.POST.get('vehicle_plate', '').strip().upper()

    with transaction.atomic():
        # select_for_update() locks this row so two simultaneous requests
        # cannot both claim the same slot.
        try:
            slot = ParkingSlot.objects.select_for_update().get(id=slot_id)
        except ParkingSlot.DoesNotExist:
            messages.error(request, "Slot not found.")
            return redirect('parking_dashboard')

        if slot.status != 'available':
            messages.error(
                request,
                "Sorry, that slot was just taken. Please choose another."
            )
            return redirect('zone_detail', zone_id=slot.zone.id)

        slot.check_in(session_token=token, vehicle_plate=vehicle_plate, hours=24)

        CheckInSession.objects.create(
            token=token,
            slot=slot,
            vehicle_plate=vehicle_plate,
        )

    messages.success(
        request,
        f"✅ Checked in to Slot {slot.slot_number} in {slot.zone.name}. "
        f"Auto-releases in 24 hours."
    )
    return redirect('zone_detail', zone_id=slot.zone.id)


# ─────────────────────────────────────────────────────────────────────────────
# Check-out  POST /parking/checkout/
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def checkout(request):
    token = request.session.get(SESSION_KEY)
    if not token:
        messages.error(request, "No active parking session found.")
        return redirect('parking_dashboard')

    slot = ParkingSlot.objects.filter(session_token=token, status='occupied').first()
    if not slot:
        messages.error(request, "No active parking session found.")
        return redirect('parking_dashboard')

    zone_id      = slot.zone.id
    slot_number  = slot.slot_number
    zone_name    = slot.zone.name

    slot.check_out()

    CheckInSession.objects.filter(token=token, is_active=True).update(
        is_active=False,
        checked_out_at=timezone.now()
    )

    messages.success(
        request,
        f"✅ Checked out from Slot {slot_number} in {zone_name}. Safe travels!"
    )
    return redirect('zone_detail', zone_id=zone_id)


# ─────────────────────────────────────────────────────────────────────────────
# JSON API — all zones  GET /parking/api/status/
# Polled by the dashboard JS every 5 seconds
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def api_status(request):
    _release_expired_slots()
    zones = ParkingZone.objects.prefetch_related('slots').all()
    token = request.session.get(SESSION_KEY)

    data = {
        'zones':       [],
        'active_slot': None,
        'timestamp':   timezone.now().isoformat(),
    }

    for zone in zones:
        data['zones'].append({
            'id':        zone.id,
            'name':      zone.name,
            'status':    zone.status,
            'occupied':  zone.occupied_count(),
            'available': zone.available_count(),
            'total':     zone.slots.count(),
            'percent':   zone.occupancy_percent(),
            'slots': [
                {
                    'id':      s.id,
                    'number':  s.slot_number,
                    'status':  s.status,
                    'is_mine': s.session_token == token if token else False,
                }
                for s in zone.slots.all()
            ],
        })

    if token:
        active = ParkingSlot.objects.filter(session_token=token, status='occupied').first()
        if active:
            data['active_slot'] = {
                'id':              active.id,
                'number':          active.slot_number,
                'zone':            active.zone.name,
                'zone_id':         active.zone.id,
                'auto_release_at': active.auto_release_at.isoformat() if active.auto_release_at else None,
            }

    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────────────────────
# JSON API — single zone  GET /parking/api/zone/<id>/
# Polled by the zone detail JS every 4 seconds
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def api_zone_status(request, zone_id):
    _release_expired_slots()
    zone  = get_object_or_404(ParkingZone, id=zone_id)
    token = request.session.get(SESSION_KEY)

    return JsonResponse({
        'id':        zone.id,
        'name':      zone.name,
        'status':    zone.status,
        'occupied':  zone.occupied_count(),
        'available': zone.available_count(),
        'total':     zone.slots.count(),
        'percent':   zone.occupancy_percent(),
        'timestamp': timezone.now().isoformat(),
        'slots': [
            {
                'id':      s.id,
                'number':  s.slot_number,
                'status':  s.status,
                'is_mine': s.session_token == token if token else False,
            }
            for s in zone.slots.all()
        ],
    })