from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('store/', views.game_list, name='game_list'),
    path('game/<slug:slug>/', views.game_detail, name='game_detail'),
    path('game/<slug:slug>/review/', views.add_review, name='add_review'),
    path('download/<int:game_id>/', views.download_game, name='download_game'),
]
