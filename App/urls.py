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
]