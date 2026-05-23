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

    # /parking/emergency_page/
    path('emergency_page/', views.emergency_page, name='emergency_page'),

    # /parking/api/report/ (POST) - Emergency reporting API
    path('api/report/', views.api_report_emergency, name='api_report_emergency'),

    # /parking/api/status/<uuid>/ - Get emergency report status
    path('api/emergency-status/<uuid:report_id>/', views.api_report_status, name='api_report_status'),

    # /parking/api/update/<uuid>/ (POST) - Update emergency status
    path('api/emergency-update/<uuid:report_id>/', views.api_update_status, name='api_update_status'),

    # /parking/api/feed/ - Live emergency feed
    path('api/emergency-feed/', views.api_live_feed, name='api_live_feed'),

    # /parking/lost-found/ - Lost & Found system
    path('lost-found/', views.lost_found, name='lost_found'),

    # /parking/api/lost-found/submit/ - Submit lost/found report
    path('api/lost-found/submit/', views.api_submit_lost_found, name='api_submit_lost_found'),

    # /parking/api/lost-found/list/ - Get lost/found reports
    path('api/lost-found/list/', views.api_lost_found_list, name='api_lost_found_list'),

    # /parking/api/lost-found/<id>/update/ - Update status
    path('api/lost-found/<uuid:report_id>/update/', views.api_update_lost_found_status, name='api_update_lost_found_status'),
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



 