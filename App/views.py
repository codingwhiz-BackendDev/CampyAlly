import uuid
import json
import random
import math
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import ParkingZone, ParkingSlot, EmergencyReport, EmergencyTimeline, LostFoundReport


# ─────────────────────────────────────────────────────────────────────────────
# Landing page  /
# ─────────────────────────────────────────────────────────────────────────────

def index(request):
    return render(request, 'index.html')


# ─────────────────────────────────────────────────────────────────────────────
# Parking dashboard  /parking/
# ─────────────────────────────────────────────────────────────────────────────

def parking_dashboard(request):
    zones = ParkingZone.objects.prefetch_related('slots').all()

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
            'detected_vehicles': z.detected_vehicles_count(),
            # Flag so JS can skip zones whose coords haven't been set yet
            'has_coords': not (z.latitude == 0.0 and z.longitude == 0.0),
        }
        for z in zones
    ])

    return render(request, 'parking_dashboard.html', {
        'zones':      zones,
        'zones_geo':  zones_geo,   # passed into template as a JS variable
    })


# ─────────────────────────────────────────────────────────────────────────────
# Zone detail  /parking/zone/<id>/
# ─────────────────────────────────────────────────────────────────────────────

def zone_detail(request, zone_id):
    zone  = get_object_or_404(ParkingZone, id=zone_id)
    slots = zone.slots.all().order_by('slot_number')

    return render(request, 'zone_detail.html', {
        'zone':        zone,
        'slots':       slots,
    })


# ─────────────────────────────────────────────────────────────────────────────
# JSON API — all zones  GET /parking/api/status/
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def api_status(request):
    zones = ParkingZone.objects.prefetch_related('slots').all()

    data = {
        'zones':       [],
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
            'detected_vehicles': zone.detected_vehicles_count(),
            'slots': [
                {
                    'id':      s.id,
                    'number':  s.slot_number,
                    'status':  s.status,
                    'detected_vehicles': s.detected_vehicles,
                    'last_detection_at': s.last_detection_at.isoformat() if s.last_detection_at else None,
                }
                for s in zone.slots.all()
            ],
        })

    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────────────────────
# JSON API — single zone  GET /parking/api/zone/<id>/
# ─────────────────────────────────────────────────────────────────────────────

@require_GET
def api_zone_status(request, zone_id):
    zone = get_object_or_404(ParkingZone, id=zone_id)

    return JsonResponse({
        'id':        zone.id,
        'name':      zone.name,
        'status':    zone.status,
        'occupied':  zone.occupied_count(),
        'available': zone.available_count(),
        'total':     zone.slots.count(),
        'percent':   zone.occupancy_percent(),
        'detected_vehicles': zone.detected_vehicles_count(),
        'timestamp': timezone.now().isoformat(),
        'slots': [
            {
                'id':      s.id,
                'number':  s.slot_number,
                'status':  s.status,
                'detected_vehicles': s.detected_vehicles,
                'last_detection_at': s.last_detection_at.isoformat() if s.last_detection_at else None,
            }
            for s in zone.slots.all()
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Security authentication views
# ─────────────────────────────────────────────────────────────────────────────

def security_login(request):
    """Login page for security personnel."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Welcome to the Security Dashboard')
            return redirect('security_dashboard')
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    
    return render(request, 'security_login.html')


def security_logout(request):
    """Logout for security personnel."""
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('security_login')


# ─────────────────────────────────────────────────────────────────────────────
# Security dashboard page  /security/
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='/security/login/')
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
    
    



def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
 
 
def _report_to_dict(r):
    return {
        'id':             str(r.id),
        'type':           r.emergency_type,
        'type_display':   r.get_emergency_type_display(),
        'severity':       r.severity,
        'status':         r.status,
        'status_display': r.get_status_display(),
        'description':    r.description,
        'reporter_name':  r.reporter_name,
        'reporter_phone': r.reporter_phone,
        'location_name':  r.location_name,
        'latitude':       r.latitude,
        'longitude':      r.longitude,
        'reported_at':    r.reported_at.isoformat(),
        'time_since':     r.time_since_reported(),
        'is_active':      r.is_active(),
        'responder_name': r.responder_name,
        'response_notes': r.response_notes,
        'timeline': [
            {
                'status':     t.status,
                'note':       t.note,
                'updated_by': t.updated_by,
                'timestamp':  t.timestamp.isoformat(),
            }
            for t in r.timeline.all()
        ],
    }
 
 
# ── Public pages ──────────────────────────────────────────────────────────────
 
def emergency_page(request):
    """Public emergency reporting page."""
    return render(request, 'emergency.html')
 
 
def emergency_dashboard(request):
    """Admin emergency control center."""
    reports  = EmergencyReport.objects.prefetch_related('timeline').all()
    active   = reports.filter(status__in=['reported', 'dispatched', 'on_scene'])
    resolved = reports.filter(status='resolved')
 
    # Analytics
    by_type = (
        reports.values('emergency_type')
               .annotate(count=Count('id'))
               .order_by('-count')
    )
    by_severity = {
        'critical': reports.filter(severity='critical').count(),
        'high':     reports.filter(severity='high').count(),
        'medium':   reports.filter(severity='medium').count(),
        'low':      reports.filter(severity='low').count(),
    }
 
    # Lost & Found integration
    lf_reports = LostFoundReport.objects.all()
    lf_active = lf_reports.filter(status='active').count()
    lf_lost_persons = lf_reports.filter(category='lost_person', status='active').count()
    lf_found_persons = lf_reports.filter(category='found_person', status='active').count()
    lf_lost_items = lf_reports.filter(category='lost_item', status='active').count()
    lf_found_items = lf_reports.filter(category='found_item', status='active').count()

    context = {
        'reports':     reports[:50],
        'active':      active,
        'resolved':    resolved,
        'total':       reports.count(),
        'active_count':   active.count(),
        'resolved_count': resolved.count(),
        'by_type':     list(by_type),
        'by_severity': by_severity,
        'lf_active': lf_active,
        'lf_lost_persons': lf_lost_persons,
        'lf_found_persons': lf_found_persons,
        'lf_lost_items': lf_lost_items,
        'lf_found_items': lf_found_items,
    }
    return render(request, 'emergency_dashboard.html', context)
 
 
# ── AJAX: submit report ───────────────────────────────────────────────────────
 
@require_POST
@csrf_exempt
def api_report_emergency(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
 
    required = ['emergency_type', 'description']
    for field in required:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'Missing {field}'}, status=400)
 
    report = EmergencyReport.objects.create(
        emergency_type  = data['emergency_type'],
        severity        = data.get('severity', 'high'),
        description     = data['description'],
        reporter_name   = data.get('reporter_name', ''),
        reporter_phone  = data.get('reporter_phone', ''),
        latitude        = data.get('latitude'),
        longitude       = data.get('longitude'),
        location_name   = data.get('location_name', ''),
        device_info     = data.get('device_info', ''),
        ip_address      = _get_client_ip(request),
        session_token   = request.session.get('session_key', ''),
    )
 
    # Create first timeline entry
    EmergencyTimeline.objects.create(
        emergency  = report,
        status     = 'reported',
        note       = 'Emergency reported via public portal.',
        updated_by = 'System',
    )
 
    return JsonResponse({
        'success':   True,
        'report_id': str(report.id),
        'message':   'Emergency reported. Help is on the way.',
        'report':    _report_to_dict(report),
    })
 
 
# ── AJAX: get live status for a report ───────────────────────────────────────
 
@require_GET
def api_report_status(request, report_id):
    report = get_object_or_404(EmergencyReport, id=report_id)
    return JsonResponse(_report_to_dict(report))
 
 
# ── AJAX: update status (admin) ───────────────────────────────────────────────
 
@require_POST
@csrf_exempt
def api_update_status(request, report_id):
    report = get_object_or_404(EmergencyReport, id=report_id)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
 
    new_status = data.get('status')
    valid = [s[0] for s in EmergencyReport.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
 
    report.status = new_status
    if new_status == 'resolved':
        report.resolved_at = timezone.now()
    if data.get('responder_name'):
        report.responder_name = data['responder_name']
    if data.get('response_notes'):
        report.response_notes = data['response_notes']
    report.save()
 
    EmergencyTimeline.objects.create(
        emergency  = report,
        status     = new_status,
        note       = data.get('note', ''),
        updated_by = data.get('updated_by', 'Admin'),
    )
 
    return JsonResponse({'success': True, 'report': _report_to_dict(report)})
 
 
# ── AJAX: live feed for dashboard ─────────────────────────────────────────────
 
@require_GET
def api_live_feed(request):
    reports = EmergencyReport.objects.prefetch_related('timeline').all()[:30]
    active_count   = EmergencyReport.objects.filter(
        status__in=['reported', 'dispatched', 'on_scene']
    ).count()
    critical_count = EmergencyReport.objects.filter(
        severity='critical', status__in=['reported', 'dispatched', 'on_scene']
    ).count()
 
    return JsonResponse({
        'reports':       [_report_to_dict(r) for r in reports],
        'active_count':  active_count,
        'critical_count': critical_count,
        'total':         EmergencyReport.objects.count(),
        'timestamp':     timezone.now().isoformat(),
    })


# ── Lost & Found System ─────────────────────────────────────────────────────────

def lost_found(request):
    """Main page for lost/found persons and items."""
    all_reports = LostFoundReport.objects.all()
    reports = all_reports.order_by('-created_at')[:50]
    
    # Get counts for dashboard
    lost_persons = all_reports.filter(category='lost_person', status='active').count()
    found_persons = all_reports.filter(category='found_person', status='active').count()
    lost_items = all_reports.filter(category='lost_item', status='active').count()
    found_items = all_reports.filter(category='found_item', status='active').count()
    
    context = {
        'reports': reports,
        'lost_persons': lost_persons,
        'found_persons': found_persons,
        'lost_items': lost_items,
        'found_items': found_items,
    }
    return render(request, 'lost_found.html', context)


def _lost_found_to_dict(report):
    """Convert LostFoundReport to dict for JSON response."""
    return {
        'id': str(report.id),
        'category': report.category,
        'category_display': report.get_category_display(),
        'title': report.title,
        'description': report.description,
        'image': report.image.url if report.image else None,
        'location': report.location,
        'date_time': report.date_time.isoformat(),
        'phone_number': report.phone_number,
        'urgency': report.urgency,
        'urgency_display': report.get_urgency_display(),
        'status': report.status,
        'status_display': report.get_status_display(),
        'age': report.age,
        'gender': report.gender,
        'gender_display': report.get_gender_display() if report.gender else None,
        'item_type': report.item_type,
        'item_type_display': report.get_item_type_display() if report.item_type else None,
        'reporter_name': report.reporter_name,
        'reporter_email': report.reporter_email,
        'latitude': report.latitude,
        'longitude': report.longitude,
        'created_at': report.created_at.isoformat(),
        'time_since': report.time_since_created(),
        'is_person': report.is_person(),
        'is_item': report.is_item(),
        'is_lost': report.is_lost(),
        'is_found': report.is_found(),
    }


@require_POST
@csrf_exempt
def api_submit_lost_found(request):
    """Submit a new lost/found report via AJAX."""
    # Handle FormData (multipart/form-data) for file uploads
    if request.content_type.startswith('multipart/form-data'):
        data = request.POST
        image = request.FILES.get('image')
    else:
        # Handle JSON data
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
        image = None
    
    required = ['category', 'title', 'description', 'location', 'phone_number']
    for field in required:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'Missing {field}'}, status=400)
    
    # Parse date_time if provided
    date_time = data.get('date_time')
    if date_time:
        from datetime import datetime
        try:
            date_time = datetime.fromisoformat(date_time)
            # Make timezone-aware
            if timezone.is_naive(date_time):
                date_time = timezone.make_aware(date_time)
        except ValueError:
            date_time = None
    
    report = LostFoundReport.objects.create(
        category=data['category'],
        title=data['title'],
        description=data['description'],
        location=data['location'],
        phone_number=data['phone_number'],
        urgency=data.get('urgency', 'medium'),
        date_time=date_time,
        reporter_name=data.get('reporter_name', ''),
        reporter_email=data.get('reporter_email', ''),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        # Person-specific
        age=data.get('age'),
        gender=data.get('gender'),
        # Item-specific
        item_type=data.get('item_type'),
        image=image,
    )
    
    return JsonResponse({
        'success': True,
        'report_id': str(report.id),
        'report': _lost_found_to_dict(report),
        'message': 'Report submitted successfully',
    })


@require_GET
def api_lost_found_list(request):
    """Get list of lost/found reports with optional filters."""
    reports = LostFoundReport.objects.all()
    
    # Filters
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if category:
        reports = reports.filter(category=category)
    if status:
        reports = reports.filter(status=status)
    if search:
        reports = reports.filter(title__icontains=search) | reports.filter(description__icontains=search)
    
    reports = reports.order_by('-created_at')[:50]
    
    return JsonResponse({
        'reports': [_lost_found_to_dict(r) for r in reports],
        'total': reports.count(),
    })


@require_POST
@csrf_exempt
def api_update_lost_found_status(request, report_id):
    """Update status of a lost/found report."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    
    report = get_object_or_404(LostFoundReport, id=report_id)
    new_status = data.get('status')
    
    valid_statuses = [s[0] for s in LostFoundReport.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    report.status = new_status
    if new_status in ('found', 'claimed', 'resolved'):
        report.resolved_at = timezone.now()
    report.save()
    
    return JsonResponse({
        'success': True,
        'report': _lost_found_to_dict(report),
        'message': f'Status updated to {report.get_status_display()}',
    })


# ─────────────────────────────────────────────────────────────────────────────
# AI Detection API  POST /parking/api/run-detection/
# Triggers YOLO on a local video file; falls back to simulated detection if
# ultralytics / video is unavailable (safe for demo without full venv).
# ─────────────────────────────────────────────────────────────────────────────

_detection_stats = {'drivers_guided': 0, 'minutes_saved': 0}


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _zone_detection_result(zone, detected_count):
    return {
        'id':       zone.id,
        'name':     zone.name,
        'detected': detected_count,
        'available': zone.available_count(),
        'occupied':  zone.occupied_count(),
        'total':     zone.slots.count(),
        'percent':   zone.occupancy_percent(),
        'status':    zone.status,
        'lat':       zone.latitude,
        'lng':       zone.longitude,
    }


@csrf_exempt
@require_POST
def api_run_detection(request):
    import os

    BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    VIDEO_PATH = os.path.join(BASE_DIR, 'traffic_video.mp4')

    zones    = list(ParkingZone.objects.prefetch_related('slots').all())
    results  = []
    simulated = False

    try:
        from .yolo_detection import YOLOVehicleDetector
        if not os.path.exists(VIDEO_PATH):
            raise FileNotFoundError("No demo video file")
        detector = YOLOVehicleDetector()
        for zone in zones:
            if not zone.slots.exists():
                continue
            count = detector.process_video_file(
                video_path=VIDEO_PATH,
                zone_id=zone.id,
                sample_frames=8,
                conf_threshold=0.25,
            )
            detector.update_zone_slots(zone_id=zone.id, vehicle_count=count)
            zone.refresh_from_db()
            results.append(_zone_detection_result(zone, count))

    except Exception:
        simulated = True
        results = []
        for zone in zones:
            slots = list(zone.slots.all())
            if not slots:
                continue
            total    = len(slots)
            detected = random.randint(int(total * 0.35), int(total * 0.95))
            for i, slot in enumerate(slots):
                if i < detected:
                    slot.status           = 'occupied'
                    slot.detected_vehicles = 1
                    slot.last_detection_at = timezone.now()
                else:
                    slot.status           = 'available'
                    slot.detected_vehicles = 0
                slot.save()
            zone.refresh_from_db()
            results.append(_zone_detection_result(zone, detected))

    # Smart Redirect — for every FULL zone, find the nearest open zone
    open_zones = [r for r in results if r['available'] > 0]
    full_zones  = [r for r in results if r['available'] == 0 and r['total'] > 0]
    redirects   = []

    for fz in full_zones:
        if not open_zones:
            break
        has_coords = fz['lat'] != 0.0 or fz['lng'] != 0.0
        if has_coords:
            def _dist(oz, _fz=fz):
                if oz['lat'] == 0.0 and oz['lng'] == 0.0:
                    return float('inf')
                return _haversine_km(_fz['lat'], _fz['lng'], oz['lat'], oz['lng'])
            best = min(open_zones, key=_dist)
        else:
            best = max(open_zones, key=lambda z: z['available'])

        saved = random.randint(4, 9)
        _detection_stats['drivers_guided'] += 1
        _detection_stats['minutes_saved']  += saved

        maps_url = (
            f"https://www.google.com/maps/dir/?api=1&destination={best['lat']},{best['lng']}"
            if (best['lat'] != 0.0 or best['lng'] != 0.0) else ''
        )
        redirects.append({
            'from_zone':    fz['name'],
            'from_id':      fz['id'],
            'to_zone':      best['name'],
            'to_id':        best['id'],
            'to_available': best['available'],
            'to_lat':       best['lat'],
            'to_lng':       best['lng'],
            'maps_url':     maps_url,
            'minutes_saved': saved,
        })

    return JsonResponse({
        'ok':        True,
        'simulated': simulated,
        'zones':     results,
        'redirects': redirects,
        'stats': {
            'drivers_guided': _detection_stats['drivers_guided'],
            'minutes_saved':  _detection_stats['minutes_saved'],
            'queue_reduced':  f"{min(len(redirects) * 15, 80)}%",
        },
        'timestamp': timezone.now().isoformat(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp webhook  GET+POST /whatsapp/webhook/
# Meta Cloud API posts inbound messages here as JSON.
# GET  — webhook verification handshake (Meta calls this once when you register)
# POST — inbound message event
# ─────────────────────────────────────────────────────────────────────────────

import os
import urllib.request as _urllib_req
import urllib.error  as _urllib_err


def _meta_send(phone_number_id: str, access_token: str, to: str, text: str):
    """Send a WhatsApp text message via Meta Graph API."""
    url     = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }).encode()
    req = _urllib_req.Request(
        url, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )
    try:
        with _urllib_req.urlopen(req, timeout=10) as resp:
            result = resp.read()
            _meta_log(f"✅ Sent to {to}")
            return result
    except _urllib_err.HTTPError as e:
        err = e.read().decode()
        _meta_log(f"❌ SEND FAILED to {to}: {e.code} {err}")
        return None
    except Exception as e:
        _meta_log(f"❌ SEND EXCEPTION to {to}: {e}")
        return None


def _meta_log(msg):
    import datetime
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
    print(f"[Meta] {msg}")
    with open("/tmp/meta_send.log", "a") as f:
        f.write(line)


def _wasender_send(to: str, text: str) -> bool:
    """Send a WhatsApp message via WaSenderAPI. Returns True on success."""
    api_key = os.environ.get("WASENDER_API_KEY", "")
    if not api_key:
        return False
    # Strip whatsapp: prefix and leading +
    phone = to.replace("whatsapp:", "").lstrip("+")
    payload = json.dumps({"to": phone, "text": text}).encode()
    req = _urllib_req.Request(
        "https://www.wasenderapi.com/api/send-message",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with _urllib_req.urlopen(req, timeout=15) as resp:
            print(f"[WaSender] ✅ Sent to {phone}")
            return True
    except _urllib_err.HTTPError as e:
        print(f"[WaSender] ❌ {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"[WaSender] ❌ {e}")
        return False


def _transcribe_voice(media_url: str, content_type: str) -> str:
    """Download a Twilio voice note and transcribe it with Groq Whisper."""
    import base64
    import tempfile
    import traceback

    # Download the audio — Twilio media requires Basic auth
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.environ.get("TWILIO_AUTH_TOKEN", "")
    req = _urllib_req.Request(media_url)
    if account_sid and auth_token:
        creds = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")

    try:
        with _urllib_req.urlopen(req, timeout=30) as resp:
            audio_data = resp.read()
    except Exception as exc:
        print(f"[Voice] Download failed: {exc}")
        return ""

    # Pick a file extension Whisper accepts
    ext = ".ogg"
    if "mp4" in content_type:
        ext = ".mp4"
    elif "mpeg" in content_type or "mp3" in content_type:
        ext = ".mp3"
    elif "wav" in content_type:
        ext = ".wav"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        from groq import Groq as _Groq
        client = _Groq()
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
                response_format="text",
            )
        transcript = result if isinstance(result, str) else result.text
        print(f"[Voice] Transcribed: {transcript!r}")
        return transcript.strip()
    except Exception as exc:
        traceback.print_exc()
        print(f"[Voice] Transcription failed: {exc}")
        return ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@csrf_exempt
def whatsapp_status(request):
    """Twilio status callback — just acknowledge delivery receipts."""
    return HttpResponse('OK', status=200)


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    """Twilio WhatsApp webhook — receives inbound messages, replies with TwiML."""
    from xml.sax.saxutils import escape
    from .whatsapp_agent import run_agent

    from_number  = request.POST.get('From', '')
    body         = (request.POST.get('Body') or '').strip()
    media_url    = request.POST.get('MediaUrl0', '')
    media_type   = request.POST.get('MediaContentType0', '')

    # Voice note — transcribe and use as body
    if media_url and 'audio' in media_type and not body:
        transcript = _transcribe_voice(media_url, media_type)
        if transcript:
            body = transcript
        else:
            body = "I sent a voice message but it could not be transcribed."

    lat = request.POST.get('Latitude')
    lng = request.POST.get('Longitude')
    user_lat = float(lat) if lat else None
    user_lng = float(lng) if lng else None
    if not body and user_lat is not None:
        body = "Here is my current location."

    reply = run_agent(from_number, body, user_lat, user_lng)

    # Try WaSender first (bypasses Twilio daily send limit).
    # If no key or send fails, fall back to TwiML reply via Twilio.
    if _wasender_send(from_number, reply):
        return HttpResponse('<Response/>', content_type='application/xml')

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Message>{escape(reply)}</Message></Response>'
    )
    return HttpResponse(twiml, content_type='application/xml')


def _transcribe_meta_voice(media_id: str, access_token: str, mime_type: str) -> str:
    """Download a Meta Cloud API voice note by media_id and transcribe with Groq Whisper."""
    import tempfile, traceback

    # Step 1 — resolve the download URL
    try:
        url_req = _urllib_req.Request(
            f"https://graph.facebook.com/v20.0/{media_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with _urllib_req.urlopen(url_req, timeout=10) as resp:
            media_info = json.loads(resp.read())
            download_url = media_info.get('url', '')
    except Exception as e:
        _meta_log(f"❌ Meta media URL fetch failed: {e}")
        return ""

    # Step 2 — download the audio bytes
    try:
        dl_req = _urllib_req.Request(
            download_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with _urllib_req.urlopen(dl_req, timeout=30) as resp:
            audio_data = resp.read()
    except Exception as e:
        _meta_log(f"❌ Meta audio download failed: {e}")
        return ""

    # Step 3 — transcribe via Groq Whisper
    ext = ".mp4" if "mp4" in mime_type else ".mp3" if ("mp3" in mime_type or "mpeg" in mime_type) else ".wav" if "wav" in mime_type else ".ogg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        from groq import Groq as _Groq
        with open(tmp_path, "rb") as f:
            result = _Groq().audio.transcriptions.create(model="whisper-large-v3", file=f, response_format="text")
        transcript = result if isinstance(result, str) else result.text
        _meta_log(f"🎤 Transcribed: {transcript!r}")
        return transcript.strip()
    except Exception as e:
        traceback.print_exc()
        _meta_log(f"❌ Meta transcription failed: {e}")
        return ""
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except Exception: pass


@csrf_exempt
def meta_whatsapp_webhook(request):
    """Meta Cloud API WhatsApp webhook — GET for verification, POST for inbound messages."""
    from .whatsapp_agent import run_agent

    verify_token   = os.environ.get('META_WEBHOOK_VERIFY_TOKEN', 'campally_verify')
    phone_number_id = os.environ.get('META_PHONE_NUMBER_ID', '')
    access_token   = os.environ.get('META_ACCESS_TOKEN', '')

    # ── Verification handshake ────────────────────────────────────────────────
    if request.method == 'GET':
        if (request.GET.get('hub.mode') == 'subscribe'
                and request.GET.get('hub.verify_token') == verify_token):
            return HttpResponse(request.GET.get('hub.challenge', ''), content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    # ── Inbound message ───────────────────────────────────────────────────────
    if request.method != 'POST':
        return HttpResponse('Method Not Allowed', status=405)

    try:
        data    = json.loads(request.body)
        msg     = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_no = msg.get('from', '')       # e.g. "2348012345678"
        mtype   = msg.get('type', 'text')

        body     = ''
        user_lat = None
        user_lng = None

        if mtype == 'text':
            body = msg.get('text', {}).get('body', '').strip()

        elif mtype == 'audio':
            media_id  = msg.get('audio', {}).get('id', '')
            mime_type = msg.get('audio', {}).get('mime_type', 'audio/ogg')
            body = (_transcribe_meta_voice(media_id, access_token, mime_type)
                    or "I sent a voice message but it could not be transcribed.")

        elif mtype == 'location':
            loc      = msg.get('location', {})
            user_lat = loc.get('latitude')
            user_lng = loc.get('longitude')
            body     = "Here is my current location."

        if body:
            reply = run_agent(from_no, body, user_lat, user_lng)
            _meta_send(phone_number_id, access_token, from_no, reply)

    except (KeyError, IndexError):
        pass  # status update or non-message event — ignore
    except Exception as e:
        _meta_log(f"❌ Webhook error: {e}")

    return HttpResponse('OK', status=200)