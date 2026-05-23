from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/<int:game_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:game_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('library/', views.library, name='library'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:game_id>/', views.toggle_wishlist, name='toggle_wishlist'),
]
