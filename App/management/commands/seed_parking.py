"""
Usage:
    python manage.py seed_parking

Creates sample zones and slots. Replace the latitude/longitude values
with real GPS coordinates from Google Maps or OpenStreetMap.

HOW TO GET REAL COORDINATES:
  1. Open https://www.openstreetmap.org
  2. Navigate to your actual parking zone location
  3. Right-click the spot → "Show address"
  4. Copy the lat/lng from the URL bar (e.g. ?mlat=6.5244&mlon=3.3792)
  5. Replace the values below and re-run this command
"""
from django.core.management.base import BaseCommand
from App.models import ParkingZone, ParkingSlot


# ── Replace these with your real zone GPS coordinates ──────────────────────
# Current values are PLACEHOLDERS — maps will show a "No coordinates set"
# message until you update these and run: python manage.py seed_parking
#
# Example for Lagos, Nigeria area (Redemption City is in Mowe, Ogun State):
#   Zone A: lat=6.8745, lng=3.4512
#
ZONES = [
    {
        'name': 'Zone A',
        'description': 'Main Gate Parking',
        'capacity': 20,
        'latitude': 6.7921,
        'longitude': 3.4478,
    },
    {
        'name': 'Zone B',
        'description': 'Auditorium Overflow Parking',
        'capacity': 20,
        'latitude': 6.7935,
        'longitude': 3.4501,
    },
    {
        'name': 'Zone C',
        'description': 'Camp Office Parking',
        'capacity': 30,
        'latitude': 6.7904,
        'longitude': 3.4526,
    },
    {
        'name': 'Zone D',
        'description': 'VIP & Accessibility Parking',
        'capacity': 10,
        'latitude': 6.7948,
        'longitude': 3.4489,
    },
]


class Command(BaseCommand):
    help = 'Seed parking zones and slots for CampEase'

    def handle(self, *args, **kwargs):
        self.stdout.write('\n🚗 Seeding CampEase parking data...\n')

        for zone_data in ZONES:
            zone, created = ParkingZone.objects.get_or_create(
                name=zone_data['name'],
                defaults={
                    'description': zone_data['description'],
                    'capacity':    zone_data['capacity'],
                    'latitude':    zone_data['latitude'],
                    'longitude':   zone_data['longitude'],
                }
            )

            if created:
                self.stdout.write(f'  ✓ Created zone: {zone.name}')
            else:
                # Update coordinates if they've been changed in the ZONES list
                zone.latitude    = zone_data['latitude']
                zone.longitude   = zone_data['longitude']
                zone.description = zone_data['description']
                zone.save()
                self.stdout.write(f'  ↺ Updated zone: {zone.name}')

            # Create slots only if zone has none
            if zone.slots.count() == 0:
                prefix = zone.name.split()[-1]  # 'A', 'B', 'C', 'D'
                for i in range(1, zone_data['capacity'] + 1):
                    ParkingSlot.objects.create(
                        zone=zone,
                        slot_number=f'{prefix}-{i:02d}',
                        status='available',
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    → Created {zone_data["capacity"]} slots'
                    )
                )
            else:
                self.stdout.write(
                    f'    → {zone.slots.count()} slots already exist, skipped'
                )

        self.stdout.write(self.style.SUCCESS('\n✅ Seed complete!\n'))
        self.stdout.write(
            self.style.WARNING(
                '⚠  Remember to update latitude/longitude in seed_parking.py\n'
                '   with real GPS coordinates, then re-run this command.\n'
                '   Or update them directly in the Django admin panel.\n'
            )
        )
