from django.db import models
from django.utils import timezone
import uuid


class ParkingZone(models.Model):
    STATUS_CHOICES = [
        ('open',    'Open'),
        ('filling', 'Filling'),
        ('full',    'Full'),
        ('closed',  'Closed'),
    ]

    name             = models.CharField(max_length=100)
    description      = models.CharField(max_length=255, blank=True)
    capacity         = models.PositiveIntegerField(default=50)
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    # GPS coordinates — update these in admin or seed command to real values
    latitude         = models.FloatField(default=0.0, help_text="Zone GPS latitude. Update to real value.")
    longitude        = models.FloatField(default=0.0, help_text="Zone GPS longitude. Update to real value.")

    # Security staff can override the auto-calculated status
    manual_override  = models.BooleanField(default=False)
    override_status  = models.CharField(max_length=10, choices=STATUS_CHOICES, blank=True, null=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def occupied_count(self):
        return self.slots.filter(status='occupied').count()

    def available_count(self):
        return self.slots.filter(status='available').count()

    def detected_vehicles_count(self):
        """Total vehicles detected by YOLO across all slots in this zone"""
        return sum(slot.detected_vehicles for slot in self.slots.all())

    def occupancy_percent(self):
        total = self.slots.count()
        if total == 0:
            return 0
        return round((self.occupied_count() / total) * 100)

    def computed_status(self):
        if self.manual_override and self.override_status:
            return self.override_status
        pct = self.occupancy_percent()
        if pct >= 100:
            return 'full'
        elif pct >= 70:
            return 'filling'
        return 'open'

    def save(self, *args, **kwargs):
        if self.pk:
            self.status = self.computed_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ParkingSlot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied',  'Occupied'),
        ('blocked',   'Blocked'),
    ]

    zone            = models.ForeignKey(ParkingZone, on_delete=models.CASCADE, related_name='slots')
    slot_number     = models.CharField(max_length=10)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
    
    # YOLO Detection fields
    detected_vehicles = models.PositiveIntegerField(default=0, help_text="Number of vehicles detected by YOLO")
    last_detection_at = models.DateTimeField(null=True, blank=True, help_text="Last time YOLO detection ran")
    confidence_score = models.FloatField(null=True, blank=True, help_text="Average confidence score of detection")
    
    updated_at      = models.DateTimeField(auto_now=True)

    def update_detection(self, vehicle_count, confidence=None):
        """Update slot with YOLO detection results"""
        self.detected_vehicles = vehicle_count
        self.last_detection_at = timezone.now()
        if confidence is not None:
            self.confidence_score = confidence
        # Update status based on detection
        if vehicle_count > 0:
            self.status = 'occupied'
        else:
            self.status = 'available'
        self.save()
        self.zone.save()

    def __str__(self):
        return f"{self.zone.name} – Slot {self.slot_number}"

    class Meta:
        ordering = ['zone', 'slot_number']
        unique_together = ['zone', 'slot_number']


    
class EmergencyReport(models.Model):
 
    EMERGENCY_TYPES = [
        ('medical',   'Medical Emergency'),
        ('fire',      'Fire Outbreak'),
        ('security',  'Security Threat'),
        ('missing',   'Missing Child'),
        ('traffic',   'Traffic Accident'),
        ('stampede',  'Crowd Stampede'),
        ('other',     'Other'),
    ]
 
    SEVERITY_LEVELS = [
        ('low',      'Low'),
        ('medium',   'Medium'),
        ('high',     'High'),
        ('critical', 'Critical'),
    ]
 
    STATUS_CHOICES = [
        ('reported',    'Reported'),
        ('dispatched',  'Dispatched'),
        ('on_scene',    'On Scene'),
        ('resolved',    'Resolved'),
        ('false_alarm', 'False Alarm'),
    ]
 
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emergency_type  = models.CharField(max_length=20, choices=EMERGENCY_TYPES)
    severity        = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='high')
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='reported')
 
    # Reporter info
    reporter_name   = models.CharField(max_length=100, blank=True)
    reporter_phone  = models.CharField(max_length=20, blank=True)
    description     = models.TextField()
 
    # Location
    latitude        = models.FloatField(null=True, blank=True)
    longitude       = models.FloatField(null=True, blank=True)
    location_name   = models.CharField(max_length=255, blank=True)
 
    # Device / meta
    device_info     = models.CharField(max_length=255, blank=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    session_token   = models.CharField(max_length=64, blank=True)
 
    # Timestamps
    reported_at     = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)
 
    # Response
    responder_name  = models.CharField(max_length=100, blank=True)
    response_notes  = models.TextField(blank=True)
    response_time_minutes = models.IntegerField(null=True, blank=True)
 
    class Meta:
        ordering = ['-reported_at']
 
    def __str__(self):
        return f"{self.get_emergency_type_display()} — {self.reported_at:%Y-%m-%d %H:%M}"
 
    def time_since_reported(self):
        delta = timezone.now() - self.reported_at
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        return f"{delta.days}d ago"
 
    def is_active(self):
        return self.status in ('reported', 'dispatched', 'on_scene')
 
 
class EmergencyTimeline(models.Model):
    """Tracks status changes for each emergency report."""
    emergency   = models.ForeignKey(EmergencyReport, on_delete=models.CASCADE, related_name='timeline')
    status      = models.CharField(max_length=15, choices=EmergencyReport.STATUS_CHOICES)
    note        = models.TextField(blank=True)
    updated_by  = models.CharField(max_length=100, blank=True, default='System')
    timestamp   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['timestamp']
 
    def __str__(self):
        return f"{self.emergency} → {self.status}"


class LostFoundReport(models.Model):
    """Unified system for lost/found persons and items."""

    CATEGORY_CHOICES = [
        ('lost_person',  'Lost Person'),
        ('found_person', 'Found Person'),
        ('lost_item',    'Lost Item'),
        ('found_item',   'Found Item'),
    ]

    ITEM_TYPE_CHOICES = [
        ('phone',      'Phone'),
        ('bag',         'Bag/Wallet'),
        ('id_card',     'ID Card'),
        ('keys',        'Keys'),
        ('book',        'Book'),
        ('clothing',    'Clothing'),
        ('electronics', 'Electronics'),
        ('jewelry',     'Jewelry'),
        ('documents',   'Documents'),
        ('other',       'Other'),
    ]

    GENDER_CHOICES = [
        ('male',   'Male'),
        ('female', 'Female'),
        ('other',  'Other'),
    ]

    URGENCY_CHOICES = [
        ('low',    'Low'),
        ('medium', 'Medium'),
        ('high',   'High'),
    ]

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('found',     'Found'),
        ('claimed',   'Claimed'),
        ('resolved',  'Resolved'),
        ('closed',    'Closed'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category        = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Common fields
    title           = models.CharField(max_length=200)
    description     = models.TextField()
    image           = models.ImageField(upload_to='lost_found/%Y/%m/', blank=True, null=True)
    location        = models.CharField(max_length=255)
    date_time       = models.DateTimeField(default=timezone.now)
    phone_number    = models.CharField(max_length=20)
    urgency         = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')

    # Person-specific fields
    age             = models.PositiveIntegerField(null=True, blank=True)
    gender          = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)

    # Item-specific fields
    item_type       = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, blank=True)

    # Reporter info
    reporter_name   = models.CharField(max_length=100, blank=True)
    reporter_email  = models.EmailField(blank=True)

    # Location (GPS)
    latitude        = models.FloatField(null=True, blank=True)
    longitude       = models.FloatField(null=True, blank=True)

    # Timestamps
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} — {self.title}"

    def time_since_created(self):
        delta = timezone.now() - self.created_at
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        return f"{delta.days}d ago"

    def is_person(self):
        return self.category in ('lost_person', 'found_person')

    def is_item(self):
        return self.category in ('lost_item', 'found_item')

    def is_lost(self):
        return self.category in ('lost_person', 'lost_item')

    def is_found(self):
        return self.category in ('found_person', 'found_item')


class WhatsAppUser(models.Model):
    phone           = models.CharField(max_length=30, unique=True)
    name            = models.CharField(max_length=100, blank=True)
    first_seen      = models.DateTimeField(auto_now_add=True)
    last_seen       = models.DateTimeField(auto_now=True)
    message_count   = models.PositiveIntegerField(default=0)
    conversation    = models.TextField(default='[]')   # JSON list of {role, content}
    saved_locations = models.TextField(default='{}')   # JSON dict of {label: {lat, lng, place_name, saved_at}}

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone})"

    class Meta:
        ordering = ['-last_seen']
        verbose_name = 'WhatsApp User'