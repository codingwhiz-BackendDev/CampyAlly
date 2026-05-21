from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ParkingZone(models.Model):
    STATUS_CHOICES = [
        ('open',    'Open'),
        ('filling', 'Filling'),
        ('full',    'Full'),
        ('closed',  'Closed'),
    ]

    name             = models.CharField(max_length=100)          # e.g. "Zone A"
    description      = models.CharField(max_length=255, blank=True)
    capacity         = models.PositiveIntegerField(default=50)
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    # Security staff can override the auto-calculated status
    manual_override  = models.BooleanField(default=False)
    override_status  = models.CharField(max_length=10, choices=STATUS_CHOICES, blank=True, null=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def occupied_count(self):
        return self.slots.filter(status='occupied').count()

    def available_count(self):
        return self.slots.filter(status='available').count()

    def occupancy_percent(self):
        total = self.slots.count()
        if total == 0:
            return 0
        return round((self.occupied_count() / total) * 100)

    def computed_status(self):
        """
        If security has set a manual override, use that.
        Otherwise calculate automatically from slot data:
          >=100% → full | >=70% → filling | else → open
        """
        if self.manual_override and self.override_status:
            return self.override_status
        pct = self.occupancy_percent()
        if pct >= 100:
            return 'full'
        elif pct >= 70:
            return 'filling'
        return 'open'

    def save(self, *args, **kwargs):
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
        ('reserved',  'Reserved'),
        ('blocked',   'Blocked'),
    ]

    zone           = models.ForeignKey(ParkingZone, on_delete=models.CASCADE, related_name='slots')
    slot_number    = models.CharField(max_length=10)     # e.g. "A-01"
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')

    # Who is parked here (optional — works for anonymous users too via session_token)
    occupied_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    occupied_at    = models.DateTimeField(null=True, blank=True)
    auto_release_at= models.DateTimeField(null=True, blank=True)

    # Anonymous users are tracked by a browser session token instead of a User account
    session_token  = models.CharField(max_length=64, blank=True, null=True)
    vehicle_plate  = models.CharField(max_length=20, blank=True, null=True)

    updated_at     = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    def check_in(self, user=None, session_token=None, vehicle_plate=None, hours=24):
        self.status          = 'occupied'
        self.occupied_by     = user
        self.session_token   = session_token
        self.vehicle_plate   = vehicle_plate
        self.occupied_at     = timezone.now()
        self.auto_release_at = timezone.now() + timezone.timedelta(hours=hours)
        self.save()
        self.zone.save()   # recalculate zone status

    def check_out(self):
        self.status          = 'available'
        self.occupied_by     = None
        self.session_token   = None
        self.vehicle_plate   = None
        self.occupied_at     = None
        self.auto_release_at = None
        self.save()
        self.zone.save()   # recalculate zone status

    def __str__(self):
        return f"{self.zone.name} – Slot {self.slot_number}"

    class Meta:
        ordering = ['zone', 'slot_number']
        unique_together = ['zone', 'slot_number']


class CheckInSession(models.Model):
    """Tracks each anonymous browser check-in so we can match check-out."""
    token          = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    slot           = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='sessions')
    vehicle_plate  = models.CharField(max_length=20, blank=True)
    checked_in_at  = models.DateTimeField(auto_now_add=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    is_active      = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {str(self.token)[:8]}… → {self.slot}"