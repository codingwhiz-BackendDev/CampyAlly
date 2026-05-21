"""
Usage:
    python manage.py seed_parking

Creates sample zones and slots for development/demo.
"""
from django.core.management.base import BaseCommand
from parking.models import ParkingZone, ParkingSlot


ZONES = [
    {'name': 'Zone A', 'description': 'Main entrance — left side', 'capacity': 20},
    {'name': 'Zone B', 'description': 'Main entrance — right side', 'capacity': 20},
    {'name': 'Zone C', 'description': 'Back field parking', 'capacity': 30},
    {'name': 'Zone D', 'description': 'VIP & accessibility', 'capacity': 10},
]


class Command(BaseCommand):
    help = 'Seed parking zones and slots for CampEase'

    def handle(self, *args, **kwargs):
        for zone_data in ZONES:
            zone, created = ParkingZone.objects.get_or_create(
                name=zone_data['name'],
                defaults={
                    'description': zone_data['description'],
                    'capacity': zone_data['capacity'],
                }
            )
            if created:
                self.stdout.write(f'Created zone: {zone.name}')
            else:
                self.stdout.write(f'Zone already exists: {zone.name}')

            # Create slots if zone is new
            existing_slots = zone.slots.count()
            if existing_slots == 0:
                prefix = zone.name.split()[-1]  # 'A', 'B', 'C', 'D'
                for i in range(1, zone_data['capacity'] + 1):
                    ParkingSlot.objects.create(
                        zone=zone,
                        slot_number=f'{prefix}-{i:02d}',
                        status='available',
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  → Created {zone_data["capacity"]} slots for {zone.name}'
                    )
                )

        self.stdout.write(self.style.SUCCESS('\n✅ Parking seed complete!'))