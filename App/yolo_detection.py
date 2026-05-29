"""
YOLO Vehicle Detection Script for ParkEase

This script uses YOLOv8 to detect vehicles in video frames and update
the parking slot database with detected vehicle counts.

For hackathon: Uses video from phone file
For production: Will use live CCTV camera feeds
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ParkEase.settings')
django.setup()

from App.models import ParkingZone, ParkingSlot
from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime


class YOLOVehicleDetector:
    """Vehicle detector using YOLOv8"""
    
    def __init__(self, model_path='yolov8n.pt'):
        """
        Initialize YOLO model
        Args:
            model_path: Path to YOLO model file (will download if not exists)
        """
        print(f"Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        print("YOLO model loaded successfully")
        
        # COCO class IDs for vehicles
        self.vehicle_classes = {
            2: 'car',
            3: 'motorcycle',
            5: 'bus',
            7: 'truck'
        }
    
    def detect_vehicles_in_frame(self, frame, conf_threshold=0.25):
        """
        Detect vehicles in a single frame
        Args:
            frame: numpy array image
            conf_threshold: Confidence threshold for detection (lower = more detections)
        Returns:
            count: Number of vehicles detected
            confidence: Average confidence score
            all_detections: List of all detections for debugging
        """
        results = self.model(frame, verbose=False, conf=conf_threshold)

        vehicle_count = 0
        total_confidence = 0
        detection_count = 0
        all_detections = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = self.model.names[class_id]

                all_detections.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence
                })

                if class_id in self.vehicle_classes:
                    vehicle_count += 1
                    total_confidence += confidence
                    detection_count += 1

        avg_confidence = total_confidence / detection_count if detection_count > 0 else None

        return vehicle_count, avg_confidence, all_detections
    
    def process_video_file(self, video_path, zone_id, sample_frames=10, conf_threshold=0.25, debug=False):
        """
        Process a video file and detect vehicles
        Args:
            video_path: Path to video file
            zone_id: ID of parking zone to update
            sample_frames: Number of frames to sample from video
            conf_threshold: Confidence threshold for detection (lower = more detections)
            debug: Print debug information about all detections
        Returns:
            avg_vehicle_count: Average vehicles detected across frames
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_indices = np.linspace(0, total_frames - 1, sample_frames, dtype=int)

        vehicle_counts = []

        print(f"Processing video: {video_path}")
        print(f"Total frames: {total_frames}, Sampling: {sample_frames} frames")
        print(f"Confidence threshold: {conf_threshold}")

        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            count, confidence, all_detections = self.detect_vehicles_in_frame(frame, conf_threshold)
            vehicle_counts.append(count)

            if debug and all_detections:
                print(f"Frame {frame_idx}: {count} vehicles detected")
                print(f"  All detections: {all_detections}")
            else:
                print(f"Frame {frame_idx}: {count} vehicles detected")

        cap.release()

        if not vehicle_counts:
            return 0

        max_count = int(np.max(vehicle_counts))
        avg_count = int(np.mean(vehicle_counts))
        print(f"Max vehicles detected: {max_count}")
        print(f"Average vehicles detected: {avg_count}")

        # Use max count for peak occupancy
        return max_count
    
    def update_zone_slots(self, zone_id, vehicle_count, confidence=None):
        """
        Update parking slots in a zone with detected vehicle count
        Args:
            zone_id: ID of parking zone
            vehicle_count: Total vehicles detected in zone
            confidence: Average confidence score
        """
        try:
            zone = ParkingZone.objects.get(id=zone_id)
            slots = zone.slots.all()
            
            if not slots.exists():
                print(f"No slots found for zone {zone.name}")
                return
            
            # Distribute vehicle count across slots
            # For simplicity, we'll distribute evenly or mark as occupied/available
            slot_count = slots.count()
            
            if vehicle_count >= slot_count:
                # All slots occupied
                for slot in slots:
                    slot.update_detection(vehicle_count=1, confidence=confidence)
            else:
                # Some slots occupied, some available
                occupied_slots = slots[:vehicle_count]
                available_slots = slots[vehicle_count:]
                
                for slot in occupied_slots:
                    slot.update_detection(vehicle_count=1, confidence=confidence)
                
                for slot in available_slots:
                    slot.update_detection(vehicle_count=0, confidence=confidence)
            
            print(f"Updated {slot_count} slots in zone {zone.name}")
            print(f"Total vehicles detected: {vehicle_count}")
            
        except ParkingZone.DoesNotExist:
            print(f"Zone with ID {zone_id} not found")
        except Exception as e:
            print(f"Error updating zone slots: {e}")


def main():
    """Main function to run YOLO detection"""

    # Configuration
    VIDEO_PATH = "traffic_video.mp4"  # Path to video file from phone
    ZONE_NAME = "Zone A"  # Target zone name (Main Gate Parking)
    MODEL_PATH = "yolov8n.pt"  # YOLOv8 nano model (fast, good for real-time)
    CONF_THRESHOLD = 0.01  # Extremely low confidence threshold for poor quality video
    DEBUG = True  # Enable debug output

    print("=" * 60)
    print("YOLO Vehicle Detection for ParkEase")
    print("=" * 60)

    # Initialize detector
    detector = YOLOVehicleDetector(model_path=MODEL_PATH)

    # Find zone by name
    try:
        zone = ParkingZone.objects.get(name=ZONE_NAME)
        ZONE_ID = zone.id
        print(f"Target zone: {zone.name} (ID: {zone.id})")
    except ParkingZone.DoesNotExist:
        print(f"\n⚠ Zone '{ZONE_NAME}' not found")
        print("Available zones:")
        for z in ParkingZone.objects.all():
            print(f"  - {z.name} (ID: {z.id})")
        return

    # Check if video file exists
    if not os.path.exists(VIDEO_PATH):
        print(f"\n⚠ Video file not found: {VIDEO_PATH}")
        print("Please place your traffic video file as 'traffic_video.mp4' in the project root")
        print("Or update the VIDEO_PATH variable in this script")
        return

    # Process video
    try:
        vehicle_count = detector.process_video_file(
            video_path=VIDEO_PATH,
            zone_id=ZONE_ID,
            sample_frames=10,
            conf_threshold=CONF_THRESHOLD,
            debug=DEBUG
        )

        # Update database
        detector.update_zone_slots(
            zone_id=ZONE_ID,
            vehicle_count=vehicle_count
        )

        print(f"\n✅ Zone {zone.name} updated: {vehicle_count} vehicles detected")

    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
