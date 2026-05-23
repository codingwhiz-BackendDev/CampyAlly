import uuid
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from .models import ParkingZone, ParkingSlot, CheckInSession


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SESSION_KEY = 'parking_session_token'


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_token(request):
    if SESSION_KEY not in request.session:
        request.session[SESSION_KEY] = uuid.uuid4().hex
    return request.session[SESSION_KEY]


def _get_active_slot(request):
    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    return ParkingSlot.objects.filter(session_token=token, status='occupied').first()


def _release_expired_slots():
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

    # Build a JSON-safe list of zone coordinates for the geofence JS.
    # Only include zones that have real coordinates set (not the 0.0 placeholder).
    zones_geo = json.dumps([
        {
            'id':        z.id,
            'name':      z.name,
            'lat':       z.latitude,
            'lng':       z.longitude,
            'url':       f'/parking/zone/{z.id}/',
            'available': z.available_count(),
            'status':    z.status,
            # Flag so JS can skip zones whose coords haven't been set yet
            'has_coords': not (z.latitude == 0.0 and z.longitude == 0.0),
        }
        for z in zones
    ])

    return render(request, 'parking_dashboard.html', {
        'zones':      zones,
        'active_slot': active_slot,
        'zones_geo':  zones_geo,   # passed into template as a JS variable
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
    token    = _get_or_create_token(request)
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
        try:
            slot = ParkingSlot.objects.select_for_update().get(id=slot_id)
        except ParkingSlot.DoesNotExist:
            messages.error(request, "Slot not found.")
            return redirect('parking_dashboard')

        if slot.status != 'available':
            messages.error(request, "Sorry, that slot was just taken. Please choose another.")
            return redirect('zone_detail', zone_id=slot.zone.id)

        slot.check_in(session_token=token, vehicle_plate=vehicle_plate, hours=24)
        CheckInSession.objects.create(token=token, slot=slot, vehicle_plate=vehicle_plate)

    messages.success(
        request,
        f"✅ Checked in to Slot {slot.slot_number} in {slot.zone.name}. Auto-releases in 24 hours."
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

    zone_id     = slot.zone.id
    slot_number = slot.slot_number
    zone_name   = slot.zone.name

    slot.check_out()
    CheckInSession.objects.filter(token=token, is_active=True).update(
        is_active=False,
        checked_out_at=timezone.now()
    )

    messages.success(request, f"✅ Checked out from Slot {slot_number} in {zone_name}. Safe travels!")
    return redirect('zone_detail', zone_id=zone_id)


# ─────────────────────────────────────────────────────────────────────────────
# JSON API — all zones  GET /parking/api/status/
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
            'lat':       zone.latitude,
            'lng':       zone.longitude,
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


# ─────────────────────────────────────────────────────────────────────────────
# Security dashboard page  /security/
# ─────────────────────────────────────────────────────────────────────────────

def security_dashboard(request):
    return render(request, 'security_dashboard.html')


# ─────────────────────────────────────────────────────────────────────────────
# Security API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


def _zone_to_dict(z):
    return {
        'id':                z.id,
        'name':              z.name,
        'description':       z.description,
        'capacity':          z.capacity,
        'status':            z.computed_status(),
        'manual_override':   z.manual_override,
        'override_status':   z.override_status,
        'occupied':          z.occupied_count(),
        'available':         z.available_count(),
        'total_slots':       z.slots.count(),
        'occupancy_percent': z.occupancy_percent(),
        'latitude':          z.latitude,
        'longitude':         z.longitude,
        'updated_at':        z.updated_at.isoformat() if z.updated_at else None,
    }


def _slot_to_dict(s):
    return {
        'id':              s.id,
        'zone':            s.zone_id,
        'zone_name':       s.zone.name,
        'slot_number':     s.slot_number,
        'status':          s.status,
        'vehicle_plate':   s.vehicle_plate,
        'occupied_at':     s.occupied_at.isoformat() if s.occupied_at else None,
        'auto_release_at': s.auto_release_at.isoformat() if s.auto_release_at else None,
        'updated_at':      s.updated_at.isoformat() if s.updated_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Security API — Zones
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_zones(request):
    if request.method == 'GET':
        zones = ParkingZone.objects.prefetch_related('slots').all()
        return JsonResponse([_zone_to_dict(z) for z in zones], safe=False)

    data = _json_body(request)
    if not data or not data.get('name'):
        return HttpResponseBadRequest('Missing zone name')

    zone = ParkingZone(
        name=data['name'],
        description=data.get('description', ''),
        capacity=data.get('capacity', 50),
        manual_override=data.get('manual_override', False),
        override_status=data.get('override_status') or None,
        latitude=data.get('latitude', 0.0),
        longitude=data.get('longitude', 0.0),
    )
    zone.save()
    return JsonResponse(_zone_to_dict(zone), status=201)


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'DELETE'])
def api_zone_detail(request, zone_id):
    zone = get_object_or_404(ParkingZone, id=zone_id)

    if request.method == 'GET':
        return JsonResponse(_zone_to_dict(zone))

    if request.method == 'DELETE':
        zone.delete()
        return JsonResponse({'ok': True})

    data = _json_body(request)
    if not data:
        return HttpResponseBadRequest('Invalid JSON')

    for field in ('name', 'description', 'capacity', 'manual_override', 'latitude', 'longitude'):
        if field in data:
            setattr(zone, field, data[field])
    if 'override_status' in data:
        zone.override_status = data['override_status'] or None

    zone.save()
    return JsonResponse(_zone_to_dict(zone))


@csrf_exempt
@require_POST
def api_zone_release(request, zone_id):
    zone = get_object_or_404(ParkingZone, id=zone_id)
    zone.slots.filter(status='occupied').update(
        status='available', occupied_by=None,
        session_token=None, vehicle_plate=None,
        occupied_at=None, auto_release_at=None,
    )
    CheckInSession.objects.filter(slot__zone=zone, is_active=True).update(
        is_active=False, checked_out_at=timezone.now()
    )
    zone.manual_override = False
    zone.override_status = None
    zone.save()
    return JsonResponse({'ok': True, 'released': True})


# ─────────────────────────────────────────────────────────────────────────────
# Security API — Slots
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_slots(request):
    if request.method == 'GET':
        qs = ParkingSlot.objects.select_related('zone').all()
        if request.GET.get('zone'):
            qs = qs.filter(zone_id=request.GET['zone'])
        return JsonResponse([_slot_to_dict(s) for s in qs], safe=False)

    data = _json_body(request)
    if not data or not data.get('zone') or not data.get('slot_number'):
        return HttpResponseBadRequest('Missing zone or slot_number')

    zone = get_object_or_404(ParkingZone, id=data['zone'])
    slot = ParkingSlot.objects.create(
        zone=zone,
        slot_number=data['slot_number'],
        status=data.get('status', 'available'),
        vehicle_plate=data.get('vehicle_plate') or None,
    )
    zone.save()
    return JsonResponse(_slot_to_dict(slot), status=201)


@csrf_exempt
@require_POST
def api_slots_bulk(request):
    data = _json_body(request)
    if not data or not data.get('zone'):
        return HttpResponseBadRequest('Missing zone')

    zone   = get_object_or_404(ParkingZone, id=data['zone'])
    prefix = data.get('prefix', '')
    start  = data.get('start', 1)
    count  = data.get('count', 10)
    status = data.get('status', 'available')
    created = 0

    for i in range(start, start + count):
        num = f"{prefix}-{str(i).zfill(2)}" if prefix else str(i).zfill(3)
        if not ParkingSlot.objects.filter(zone=zone, slot_number=num).exists():
            ParkingSlot.objects.create(zone=zone, slot_number=num, status=status)
            created += 1

    zone.save()
    return JsonResponse({'ok': True, 'created': created})


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'DELETE'])
def api_slot_detail(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)

    if request.method == 'GET':
        return JsonResponse(_slot_to_dict(slot))

    if request.method == 'DELETE':
        zone = slot.zone
        slot.delete()
        zone.save()
        return JsonResponse({'ok': True})

    data = _json_body(request)
    if not data:
        return HttpResponseBadRequest('Invalid JSON')

    if 'zone' in data:
        slot.zone = get_object_or_404(ParkingZone, id=data['zone'])
    for field in ('slot_number', 'status', 'vehicle_plate'):
        if field in data:
            setattr(slot, field, data[field] or None)

    slot.save()
    slot.zone.save()
    return JsonResponse(_slot_to_dict(slot))


@csrf_exempt
@require_POST
def api_slot_checkout(request, slot_id):
    slot = get_object_or_404(ParkingSlot, id=slot_id)
    slot.check_out()
    CheckInSession.objects.filter(slot=slot, is_active=True).update(
        is_active=False, checked_out_at=timezone.now()
    )
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────────────────────────────────────
# Security API — Sessions
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def api_sessions(request):
    sessions = CheckInSession.objects.select_related('slot', 'slot__zone').order_by('-checked_in_at')[:100]
    return JsonResponse([
        {
            'token_short':    str(s.token)[:12] + '…',
            'slot_label':     str(s.slot),
            'vehicle_plate':  s.vehicle_plate,
            'checked_in_at':  s.checked_in_at.isoformat() if s.checked_in_at else None,
            'checked_out_at': s.checked_out_at.isoformat() if s.checked_out_at else None,
            'is_active':      s.is_active,
        }
        for s in sessions
    ], safe=False)
    
    
def emergency_dashboard(request):
    return render(request, 'emergency_dashboard.html')