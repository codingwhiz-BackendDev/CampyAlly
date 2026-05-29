"""
Django management command to run YOLO vehicle detection periodically

This command should be run every 5 minutes to update parking slot
occupancy based on YOLO vehicle detection from video feeds.

Usage:
    python manage.py run_yolo_detection

For periodic execution (every 5 minutes), use cron or a task scheduler:
    */5 * * * * cd /path/to/ParkEase && python manage.py run_yolo_detection
"""

import os
import sys
from django.core.management.base import BaseCommand
from App.yolo_detection import YOLOVehicleDetector
from App.models import ParkingZone
from pathlib import Path


class Command(BaseCommand):
    help = 'Run YOLO vehicle detection to update parking slot occupancy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--video-path',
            type=str,
            default='traffic_video.mp4',
            help='Path to video file for detection (default: traffic_video.mp4)'
        )
        parser.add_argument(
            '--zone-id',
            type=int,
            default=None,
            help='Specific zone ID to update (default: all zones)'
        )
        parser.add_argument(
            '--zone-name',
            type=str,
            default=None,
            help='Specific zone name to update (default: all zones)'
        )
        parser.add_argument(
            '--model-path',
            type=str,
            default='yolov8n.pt',
            help='Path to YOLO model file (default: yolov8n.pt)'
        )
        parser.add_argument(
            '--sample-frames',
            type=int,
            default=10,
            help='Number of frames to sample from video (default: 10)'
        )
        parser.add_argument(
            '--conf-threshold',
            type=float,
            default=0.01,
            help='Confidence threshold for detection (lower = more detections, default: 0.01)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug output to show all detections'
        )

    def handle(self, *args, **options):
        video_path = options['video_path']
        zone_id = options['zone_id']
        zone_name = options['zone_name']
        model_path = options['model_path']
        sample_frames = options['sample_frames']
        conf_threshold = options['conf_threshold']
        debug = options['debug']

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Starting YOLO Vehicle Detection'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Check if video file exists
        if not os.path.exists(video_path):
            self.stdout.write(
                self.style.ERROR(f'⚠ Video file not found: {video_path}')
            )
            self.stdout.write(
                self.style.WARNING('Please place your traffic video file in the project root')
            )
            return

        # Initialize detector
        try:
            detector = YOLOVehicleDetector(model_path=model_path)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to initialize YOLO model: {e}')
            )
            return

        # Get zones to update
        if zone_id:
            try:
                zones = [ParkingZone.objects.get(id=zone_id)]
                self.stdout.write(f'Processing zone: {zones[0].name}')
            except ParkingZone.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Zone with ID {zone_id} not found')
                )
                return
        elif zone_name:
            try:
                zones = [ParkingZone.objects.get(name=zone_name)]
                self.stdout.write(f'Processing zone: {zones[0].name}')
            except ParkingZone.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Zone with name "{zone_name}" not found')
                )
                self.stdout.write('Available zones:')
                for z in ParkingZone.objects.all():
                    self.stdout.write(f'  - {z.name} (ID: {z.id})')
                return
        else:
            zones = ParkingZone.objects.all()
            self.stdout.write(f'Processing {zones.count()} zones')

        # Process each zone
        for zone in zones:
            self.stdout.write(f'\nProcessing zone: {zone.name}')

            try:
                # Process video and get vehicle count
                vehicle_count = detector.process_video_file(
                    video_path=video_path,
                    zone_id=zone.id,
                    sample_frames=sample_frames,
                    conf_threshold=conf_threshold,
                    debug=debug
                )

                # Update zone slots
                detector.update_zone_slots(
                    zone_id=zone.id,
                    vehicle_count=vehicle_count
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Zone {zone.name} updated: {vehicle_count} vehicles detected'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing zone {zone.name}: {e}')
                )
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('YOLO Detection Complete'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
