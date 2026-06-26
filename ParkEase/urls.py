from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from App import views as landing_views
from App.urls import security_urlpatterns
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_views.index, name='index'),
    path('parking/', include('App.urls')),
    path('security/login/', landing_views.security_login, name='security_login'),
    path('security/logout/', landing_views.security_logout, name='security_logout'),
    path('security/', landing_views.security_dashboard, name='security_dashboard'),
    path('security/', include(security_urlpatterns)),
    path('emergency/', landing_views.emergency_page, name='emergency_page'),
    path('emergency_dashboard/', landing_views.emergency_dashboard, name='emergency_dashboard'),
    path('lost-person/', landing_views.lost_found, name='lost_person'),

    # WhatsApp — Twilio inbound
    path('whatsapp/webhook/', landing_views.whatsapp_webhook, name='whatsapp_webhook'),

    # WhatsApp — Twilio status callback
    path('whatsapp/status/', landing_views.whatsapp_status, name='whatsapp_status'),

    # WhatsApp — Meta Cloud API
    path('whatsapp/meta/', landing_views.meta_whatsapp_webhook, name='meta_whatsapp_webhook'),

    # WhatsApp — Baileys (QR code, no Twilio/Meta needed)
    path('whatsapp/baileys/', landing_views.baileys_webhook, name='baileys_webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)