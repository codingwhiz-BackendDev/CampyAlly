"""
Script to update Zone A to have 100 parking slots
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ParkEase.settings')
django.setup()

from App.models import ParkingZone, ParkingSlot

def update_zone_a_to_100_slots():
    """Update Zone A to have 100 parking slots"""
    
    try:
        # Find Zone A
        zone = ParkingZone.objects.get(name="Zone A")
        print(f"Found zone: {zone.name}")
        print(f"Current capacity: {zone.capacity}")
        print(f"Current slot count: {zone.slots.count()}")
        
        # Update capacity to 100
        zone.capacity = 100
        zone.save()
        print(f"Updated capacity to: {zone.capacity}")
        
        # Get current slots
        current_slots = zone.slots.all()
        current_count = current_slots.count()
        
        if current_count < 100:
            # Create additional slots
            slots_to_create = 100 - current_count
            print(f"Creating {slots_to_create} additional slots...")
            
            for i in range(slots_to_create):
                slot_number = str(current_count + i + 1)
                ParkingSlot.objects.create(
                    zone=zone,
                    slot_number=slot_number,
                    status='available'
                )
            
            print(f"✅ Successfully created {slots_to_create} slots")
        elif current_count > 100:
            # Remove excess slots
            slots_to_remove = current_count - 100
            print(f"Removing {slots_to_remove} excess slots...")
            
            excess_slots = current_slots[100:]
            for slot in excess_slots:
                slot.delete()
            
            print(f"✅ Successfully removed {slots_to_remove} slots")
        else:
            print("Zone A already has exactly 100 slots")
        
        print(f"\nFinal slot count: {zone.slots.count()}")
        print(f"Available slots: {zone.available_count()}")
        print(f"Occupied slots: {zone.occupied_count()}")
        
    except ParkingZone.DoesNotExist:
        print("❌ Zone A not found in database")
        print("\nAvailable zones:")
        for z in ParkingZone.objects.all():
            print(f"  - {z.name} (ID: {z.id})")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_zone_a_to_100_slots()
