from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Steam Clone API",
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('games.urls')),
    path('users/', include('users.urls')),
    path('cart/', include('cart.urls')),
    path('inventory/', include('inventory.urls')),
    path('trades/', include('trades.urls')),
    path('friends/', include('friends.urls')),
    path('chat/', include('chat.urls')),
    path('market/', include('marketplace.urls')),
    path('wallet/', include('wallet.urls')),
    path('notifications/', include('notifications.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('launcher-api/', include('launcher_api.urls')),


    # 🔥 Swagger
   
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)