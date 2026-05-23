from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import ParkingZone, ParkingSlot, CheckInSession,EmergencyReport,EmergencyTimeline,LostFoundReport


# ── Zone admin ────────────────────────────────────────────────────────────────

@admin.register(ParkingZone)
class ParkingZoneAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'occupied_count', 'available_count',
        'occupancy_bar', 'status_badge', 'manual_override', 'updated_at',
    )
    list_filter   = ('status', 'manual_override')
    search_fields = ('name',)
    readonly_fields = ('status', 'updated_at')
    # Removed inline to prevent "needs primary key" error when creating new zones
    # Use the security dashboard at /security/ to manage slots instead

    fieldsets = (
        ('Zone Info', {
            'fields': ('name', 'description', 'capacity', 'status', 'updated_at'),
        }),
        ('🔒 Security Override', {
            'description': (
                'Enable this to manually set the zone status shown to the public. '
                'Useful when security staff are directing traffic and the slot count '
                'does not yet reflect reality. Disable to return to automatic mode.'
            ),
            'fields':  ('manual_override', 'override_status'),
            'classes': ('collapse',),
        }),
    )

    # ── Computed columns ─────────────────────────────────────────────────────

    def occupied_count(self, obj):
        return obj.occupied_count()
    occupied_count.short_description = 'Occupied'

    def available_count(self, obj):
        return obj.available_count()
    available_count.short_description = 'Available'

    def occupancy_bar(self, obj):
        pct = obj.occupancy_percent()
        color = '#e74c3c' if pct >= 100 else ('#f39c12' if pct >= 70 else '#27ae60')
        return format_html(
            '<div style="width:120px;background:#eee;border-radius:4px;overflow:hidden;">'
            '<div style="width:{pct}%;background:{color};height:14px;"></div></div>'
            '<small style="color:#666">{pct}%</small>',
            pct=min(pct, 100), color=color,
        )
    occupancy_bar.short_description = 'Occupancy'

    def status_badge(self, obj):
        colors = {
            'open':    ('#27ae60', 'Open'),
            'filling': ('#f39c12', 'Filling'),
            'full':    ('#e74c3c', 'Full'),
            'closed':  ('#7f8c8d', 'Closed'),
        }
        color, label = colors.get(obj.status, ('#999', obj.status))
        return format_html(
            '<span style="background:{c};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:700;">{l}</span>',
            c=color, l=label,
        )
    status_badge.short_description = 'Status'

    # ── Save hook — keep status in sync ──────────────────────────────────────

    def save_model(self, request, obj, form, change):
        obj.status = obj.computed_status()
        super().save_model(request, obj, form, change)

    # ── Bulk actions for security staff ──────────────────────────────────────

    actions = ['mark_open', 'mark_filling', 'mark_full', 'release_all_slots']

    def mark_open(self, request, queryset):
        for z in queryset:
            z.manual_override = True
            z.override_status = 'open'
            z.save()
        self.message_user(request, f"{queryset.count()} zone(s) marked Open.")
    mark_open.short_description = "🟢 Mark selected zones — Open"

    def mark_filling(self, request, queryset):
        for z in queryset:
            z.manual_override = True
            z.override_status = 'filling'
            z.save()
        self.message_user(request, f"{queryset.count()} zone(s) marked Filling.")
    mark_filling.short_description = "🟡 Mark selected zones — Filling"

    def mark_full(self, request, queryset):
        for z in queryset:
            z.manual_override = True
            z.override_status = 'full'
            z.save()
        self.message_user(request, f"{queryset.count()} zone(s) marked Full.")
    mark_full.short_description = "🔴 Mark selected zones — Full"

    def release_all_slots(self, request, queryset):
        """End of day — clear every occupied slot in selected zones."""
        for zone in queryset:
            zone.slots.filter(status='occupied').update(
                status='available',
                occupied_by=None,
                session_token=None,
                vehicle_plate=None,
                occupied_at=None,
                auto_release_at=None,
            )
            zone.manual_override = False
            zone.override_status = None
            zone.save()
        self.message_user(request, "All slots released for selected zones.")
    release_all_slots.short_description = "♻️ Release all slots (end of day)"


# ── Slot admin ────────────────────────────────────────────────────────────────

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display  = (
        'slot_number', 'zone', 'status_badge',
        'vehicle_plate', 'occupied_at', 'time_remaining',
    )
    list_filter   = ('status', 'zone')
    search_fields = ('slot_number', 'vehicle_plate')
    readonly_fields = ('occupied_at', 'updated_at')
    actions       = ['force_checkout']

    def status_badge(self, obj):
        colors = {
            'available': ('#27ae60', 'Available'),
            'occupied':  ('#e74c3c', 'Occupied'),
            'reserved':  ('#3498db', 'Reserved'),
            'blocked':   ('#7f8c8d', 'Blocked'),
        }
        color, label = colors.get(obj.status, ('#999', obj.status))
        return format_html(
            '<span style="background:{c};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{l}</span>',
            c=color, l=label,
        )
    status_badge.short_description = 'Status'

    def time_remaining(self, obj):
        if not obj.auto_release_at:
            return '—'
        remaining = obj.auto_release_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return format_html('<span style="color:red;">⚠ Expired</span>')
        h, rem = divmod(int(remaining.total_seconds()), 3600)
        m = rem // 60
        return f"{h}h {m}m"
    time_remaining.short_description = 'Auto-release in'

    def force_checkout(self, request, queryset):
        for slot in queryset:
            slot.check_out()
        self.message_user(request, f"{queryset.count()} slot(s) checked out.")
    force_checkout.short_description = "⬅ Force check-out selected slots"


# ── Session admin ─────────────────────────────────────────────────────────────

@admin.register(CheckInSession)
class CheckInSessionAdmin(admin.ModelAdmin):
    list_display  = ('token_short', 'slot', 'vehicle_plate', 'checked_in_at', 'is_active')
    list_filter   = ('is_active',)
    readonly_fields = ('token', 'checked_in_at')

    def token_short(self, obj):
        return f"{str(obj.token)[:12]}…"
    token_short.short_description = 'Session'
    
    


admin.site.register(EmergencyReport)
admin.site.register(EmergencyTimeline)


# ── Lost & Found Admin ─────────────────────────────────────────────────────────

@admin.register(LostFoundReport)
class LostFoundReportAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'status', 'urgency',
        'location', 'phone_number', 'created_at'
    )
    list_filter = ('category', 'status', 'urgency', 'created_at')
    search_fields = ('title', 'description', 'location', 'reporter_name')
    readonly_fields = ('created_at', 'updated_at', 'time_since_created')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'title', 'description', 'image')
        }),
        ('Location & Contact', {
            'fields': ('location', 'latitude', 'longitude', 'phone_number', 'date_time')
        }),
        ('Status & Urgency', {
            'fields': ('status', 'urgency', 'resolved_at')
        }),
        ('Person Details', {
            'fields': ('age', 'gender'),
            'classes': ('collapse',)
        }),
        ('Item Details', {
            'fields': ('item_type',),
            'classes': ('collapse',)
        }),
        ('Reporter Information', {
            'fields': ('reporter_name', 'reporter_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def time_since_created(self, obj):
        return obj.time_since_created()
    time_since_created.short_description = 'Time Since'