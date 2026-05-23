from django.urls import path
from . import views

# These are all mounted under /parking/ by the project urls.py
urlpatterns = [
    # /parking/
    path('', views.parking_dashboard, name='parking_dashboard'),

    # /parking/zone/1/
    path('zone/<int:zone_id>/', views.zone_detail, name='zone_detail'),

    # /parking/checkin/5/   (POST only)
    path('checkin/<int:slot_id>/', views.checkin, name='checkin'),

    # /parking/checkout/    (POST only)
    path('checkout/', views.checkout, name='checkout'),

    # /parking/api/status/
    path('api/status/', views.api_status, name='api_status'),

    # /parking/api/zone/1/
    path('api/zone/<int:zone_id>/', views.api_zone_status, name='api_zone_status'),
    
    #emergency
    path('emergency_dashboard', views.emergency_dashboard, name='emergency_dashboard')
]

# Security API routes (mounted separately)
security_urlpatterns = [
    # /security/api/zones
    path('api/zones/', views.api_zones, name='api_zones'),

    # /security/api/zones/1
    path('api/zones/<int:zone_id>/', views.api_zone_detail, name='api_zone_detail'),

    # /security/api/zones/1/release
    path('api/zones/<int:zone_id>/release/', views.api_zone_release, name='api_zone_release'),

    # /security/api/slots
    path('api/slots/', views.api_slots, name='api_slots'),

    # /security/api/slots/bulk
    path('api/slots/bulk/', views.api_slots_bulk, name='api_slots_bulk'),

    # /security/api/slots/1
    path('api/slots/<int:slot_id>/', views.api_slot_detail, name='api_slot_detail'),

    # /security/api/slots/1/checkout
    path('api/slots/<int:slot_id>/checkout/', views.api_slot_checkout, name='api_slot_checkout'),

    # /security/api/sessions
    path('api/sessions/', views.api_sessions, name='api_sessions'),
]