"""
Seed the real Redemption City (RCCG camp) car parks with GPS coordinates so the
parking dashboard, geofence nudges, and the WhatsApp agent's "nearest car park"
routing all work with authentic locations.

Usage:
    python manage.py seed_redemption_parking          # create/update zones + slots
    python manage.py seed_redemption_parking --reset   # delete existing zones first

Coordinates are approximate (camp is on the Lagos-Ibadan Expressway, Mowe,
Ogun State) — accurate enough for demo routing/distance, not survey-grade.
"""

import random

from django.core.management.base import BaseCommand
from App.models import ParkingZone, ParkingSlot

# name, description, real capacity (for display), lat, lng, demo slot count
CAR_PARKS = [
    ("Car Park A",  "Old Auditorium parking",                     1200,  6.8932, 3.5083, 30),
    ("Car Park B",  "Old Auditorium parking",                     1200,  6.8926, 3.5096, 30),
    ("Car Park C",  "Expressway-entrance landmark & bus stop",    1500,  6.8897, 3.5061, 30),
    ("Car Park D",  "National Youth Centre event grounds",         900,  6.8974, 3.5139, 24),
    ("Car Park F",  "Convention overflow parking",                1000,  6.8951, 3.5121, 24),
    ("Car Park V",  "New Auditorium (Arena) parking",             5000,  6.9048, 3.5198, 40),
    ("New Arena Parking", "New Auditorium — 15,000+ cars + basement", 15000, 6.9079, 3.5181, 50),
    ("Odofin Car Park",   "Near the New Auditorium",                800,  6.9031, 3.5229, 24),
]


class Command(BaseCommand):
    help = "Seed authentic Redemption City car parks with GPS coordinates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete all existing parking zones before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            count = ParkingZone.objects.count()
            ParkingZone.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing zones."))

        for name, desc, capacity, lat, lng, n_slots in CAR_PARKS:
            zone, created = ParkingZone.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "capacity": capacity,
                    "latitude": lat,
                    "longitude": lng,
                },
            )
            # Keep coordinates / description current even on re-runs.
            zone.description = desc
            zone.capacity = capacity
            zone.latitude = lat
            zone.longitude = lng

            existing = zone.slots.count()
            for i in range(existing, n_slots):
                ParkingSlot.objects.get_or_create(
                    zone=zone, slot_number=f"{i + 1:02d}",
                )

            # Give the demo a lifelike mix of occupancy (~25–80% full).
            slots = list(zone.slots.all())
            occ_fraction = random.uniform(0.25, 0.8)
            n_occupied = int(len(slots) * occ_fraction)
            random.shuffle(slots)
            for idx, slot in enumerate(slots):
                slot.status = "occupied" if idx < n_occupied else "available"
                slot.save()

            zone.save()  # recomputes status from occupancy
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(
                f"{verb} {zone.name}: {zone.available_count()} free / "
                f"{zone.slots.count()} slots ({zone.get_status_display()})"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {ParkingZone.objects.count()} car parks ready."
        ))
