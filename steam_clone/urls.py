from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title='Steam Clone API',
        default_version='v1',
        description=(
            'REST API для Steam Clone.\n\n'
            '**Авторизация:** получите токен через `POST /api/auth/login/`, '
            'затем в Swagger нажмите **Authorize** и введите: `Token <ваш_токен>`.\n\n'
            'Публичные эндпоинты: игры, категории, теги, отзывы (чтение).\n'
            'Нужен токен: корзина, wishlist, профиль, создание отзывов.'
        ),
        contact=openapi.Contact(email='support@steam-clone.local'),
        license=openapi.License(name='MIT License'),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger / ReDoc / OpenAPI schema
    re_path(
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    path(
        'swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    path(
        'redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc',
    ),

    # REST API
    path('api/', include('api.urls')),

    # Site
    path('', include('games.urls')),
    path('users/', include('users.urls')),
    path('cart/', include('cart.urls')),
    path('inventory/', include('inventory.urls')),
    path('trades/', include('trades.urls')),
    path('friends/', include('friends.urls')),
    path('chat/', include('chat.urls')),
    path('groups/', include('groups.urls', namespace='groups')),
    path('market/', include('marketplace.urls')),
    path('wallet/', include(('wallet.urls', 'wallet'), namespace='wallet')),
    path('notifications/', include('notifications.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('launcher-api/', include('launcher_api.urls')),
    path('plus/', include('steamplus.urls')),
    path('support/', include('support.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
