from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='api-category')
router.register(r'tags', views.TagViewSet, basename='api-tag')
router.register(r'games', views.GameViewSet, basename='api-game')
router.register(r'reviews', views.ReviewViewSet, basename='api-review')
router.register(r'cart', views.CartViewSet, basename='api-cart')
router.register(r'wishlist', views.WishlistViewSet, basename='api-wishlist')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', views.login_api, name='api-login'),
    path('auth/register/', views.register_api, name='api-register'),
    path('auth/me/', views.me, name='api-me'),
]
