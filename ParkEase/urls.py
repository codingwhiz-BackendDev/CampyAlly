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
    path('security/', landing_views.security_dashboard, name='security_dashboard'),
    path('security/', include(security_urlpatterns)),
    path('emergency_dashboard/', landing_views.emergency_dashboard, name ='landing_views')
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)