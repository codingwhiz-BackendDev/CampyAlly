"""
Django management command to update Zone A to 100 parking slots

Usage:
    python manage.py update_zone_a_slots
"""

from django.core.management.base import BaseCommand
from App.models import ParkingZone, ParkingSlot


class Command(BaseCommand):
    help = 'Update Zone A to have 100 parking slots'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Updating Zone A to 100 Slots'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        try:
            # Find Zone A
            zone = ParkingZone.objects.get(name="Zone A")
            self.stdout.write(f'Found zone: {zone.name}')
            self.stdout.write(f'Current capacity: {zone.capacity}')
            self.stdout.write(f'Current slot count: {zone.slots.count()}')
            
            # Update capacity to 100
            zone.capacity = 100
            zone.save()
            self.stdout.write(f'Updated capacity to: {zone.capacity}')
            
            # Get current slots
            current_slots = zone.slots.all()
            current_count = current_slots.count()
            
            if current_count < 100:
                # Create additional slots
                slots_to_create = 100 - current_count
                self.stdout.write(f'Creating {slots_to_create} additional slots...')
                
                for i in range(slots_to_create):
                    slot_number = str(current_count + i + 1)
                    ParkingSlot.objects.create(
                        zone=zone,
                        slot_number=slot_number,
                        status='available'
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully created {slots_to_create} slots')
                )
            elif current_count > 100:
                # Remove excess slots
                slots_to_remove = current_count - 100
                self.stdout.write(f'Removing {slots_to_remove} excess slots...')
                
                excess_slots = current_slots[100:]
                for slot in excess_slots:
                    slot.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully removed {slots_to_remove} slots')
                )
            else:
                self.stdout.write('Zone A already has exactly 100 slots')
            
            self.stdout.write(f'\nFinal slot count: {zone.slots.count()}')
            self.stdout.write(f'Available slots: {zone.available_count()}')
            self.stdout.write(f'Occupied slots: {zone.occupied_count()}')
            
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('Zone A Update Complete'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            
        except ParkingZone.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ Zone A not found in database')
            )
            self.stdout.write('\nAvailable zones:')
            for z in ParkingZone.objects.all():
                self.stdout.write(f'  - {z.name} (ID: {z.id})')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            )
            import traceback
            traceback.print_exc()
