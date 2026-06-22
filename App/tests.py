import json
import xml.etree.ElementTree as ET
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from App.models import ParkingZone, ParkingSlot, EmergencyReport, LostFoundReport
from App.whatsapp_agent import (
    run_agent,
    _tool_get_available_parking,
    _tool_find_nearest_open_zone,
    _tool_report_emergency,
    _tool_report_lost_found,
)


class ParkingModelTests(TestCase):
    def setUp(self):
        # Create a zone
        self.zone = ParkingZone.objects.create(
            name="Test Zone",
            description="Test Description",
            capacity=10,
            latitude=6.8900,
            longitude=3.5000,
        )
        # Create 5 slots: 3 occupied, 2 available
        self.slots = []
        for i in range(5):
            status = "occupied" if i < 3 else "available"
            slot = ParkingSlot.objects.create(
                zone=self.zone,
                slot_number=f"{i+1:02d}",
                status=status,
                detected_vehicles=1 if status == "occupied" else 0,
            )
            self.slots.append(slot)

    def test_zone_counts(self):
        self.assertEqual(self.zone.slots.count(), 5)
        self.assertEqual(self.zone.occupied_count(), 3)
        self.assertEqual(self.zone.available_count(), 2)
        self.assertEqual(self.zone.occupancy_percent(), 60)
        self.assertEqual(self.zone.computed_status(), "open")

    def test_zone_computed_status_filling(self):
        # Add occupied slots to exceed 70% occupancy
        for slot in self.slots[3:]:
            slot.status = "occupied"
            slot.save()
        self.zone.refresh_from_db()
        self.assertEqual(self.zone.occupancy_percent(), 100)
        # Verify computed status is full (since occupancy is 100)
        self.assertEqual(self.zone.computed_status(), "full")

    def test_slot_update_detection(self):
        slot = self.slots[3]  # currently available
        slot.update_detection(vehicle_count=1, confidence=0.85)
        self.assertEqual(slot.status, "occupied")
        self.assertEqual(slot.detected_vehicles, 1)
        self.assertEqual(slot.confidence_score, 0.85)
        self.assertIsNotNone(slot.last_detection_at)


class AIDetectionAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.zone1 = ParkingZone.objects.create(
            name="Zone 1", capacity=10, latitude=6.8900, longitude=3.5000
        )
        self.slot1 = ParkingSlot.objects.create(
            zone=self.zone1, slot_number="01", status="available"
        )
        self.zone2 = ParkingZone.objects.create(
            name="Zone 2", capacity=10, latitude=6.8910, longitude=3.5010
        )
        self.slot2 = ParkingSlot.objects.create(
            zone=self.zone2, slot_number="01", status="available"
        )

    @patch("os.path.exists")
    def test_api_run_detection_simulated_fallback(self, mock_exists):
        # Force video path non-existence to trigger simulated path
        mock_exists.return_value = False

        url = reverse("api_run_detection")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        self.assertTrue(data["simulated"])
        self.assertEqual(len(data["zones"]), 2)

        # Check there are no duplicate zones in results
        zone_ids = [z["id"] for z in data["zones"]]
        self.assertEqual(len(zone_ids), len(set(zone_ids)))


class WhatsAppWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create some zones to avoid errors in tools
        self.zone = ParkingZone.objects.create(
            name="Car Park C", capacity=10, latitude=6.8897, longitude=3.5061
        )
        ParkingSlot.objects.create(zone=self.zone, slot_number="01", status="available")

    @patch("App.whatsapp_agent.run_agent")
    def test_whatsapp_webhook_post(self, mock_run_agent):
        mock_run_agent.return_value = "Hello from CampAlly! 🅿️"

        url = reverse("whatsapp_webhook")
        payload = {
            "From": "whatsapp:+2348012345678",
            "Body": "hi",
            "ProfileName": "Timilehin",
        }
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/xml")

        # Parse TwiML response
        root = ET.fromstring(response.content)
        self.assertEqual(root.tag, "Response")
        message_el = root.find("Message")
        self.assertIsNotNone(message_el)
        self.assertEqual(message_el.text, "Hello from CampAlly! 🅿️")


class WhatsAppAgentTests(TestCase):
    def setUp(self):
        # Setup zones
        self.zone_c = ParkingZone.objects.create(
            name="Car Park C", capacity=10, latitude=6.8897, longitude=3.5061
        )
        self.slot_c = ParkingSlot.objects.create(
            zone=self.zone_c, slot_number="01", status="available"
        )
        self.zone_v = ParkingZone.objects.create(
            name="Car Park V", capacity=10, latitude=6.9048, longitude=3.5198
        )
        self.slot_v = ParkingSlot.objects.create(
            zone=self.zone_v, slot_number="01", status="available"
        )

    def test_tool_get_available_parking(self):
        res = _tool_get_available_parking()
        self.assertIn("Car Park C", res)
        self.assertIn("Car Park V", res)

    def test_tool_find_nearest_open_zone(self):
        # User is at 6.8900, 3.5060 (very close to Car Park C: 6.8897, 3.5061)
        res = _tool_find_nearest_open_zone(user_lat=6.8900, user_lng=3.5060)
        self.assertIn("Car Park C", res)
        self.assertIn("Directions:", res)

    def test_tool_report_emergency(self):
        res = _tool_report_emergency(
            emergency_type="medical",
            description="Person collapsed near expressway entrance",
            location_name="Car Park C",
            reporter_phone="+2348012345678",
        )
        self.assertIn("Emergency logged", res)

        # Check DB
        report = EmergencyReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.emergency_type, "medical")
        self.assertEqual(report.location_name, "Car Park C")
        self.assertEqual(report.reporter_phone, "+2348012345678")

    def test_tool_report_lost_found(self):
        res = _tool_report_lost_found(
            category="lost_item",
            title="Black Wallet",
            description="Lost brown leather wallet with ID cards",
            location="Car Park V",
            phone_number="+2348012345678",
        )
        self.assertIn("Lost Item report filed", res)

        # Check DB
        report = LostFoundReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.category, "lost_item")
        self.assertEqual(report.title, "Black Wallet")
        self.assertEqual(report.location, "Car Park V")
        self.assertEqual(report.phone_number, "+2348012345678")
