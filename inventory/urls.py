from django.urls import path
from .views import inventory_view, toggle_showcase_view

urlpatterns = [
    path('', inventory_view, name='inventory'),
    path('showcase/<int:item_id>/', toggle_showcase_view, name='toggle_showcase'),
]