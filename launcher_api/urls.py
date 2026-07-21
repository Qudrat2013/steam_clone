from django.urls import path
from . import views

urlpatterns = [
    # Теперь страница будет доступна по пути: http://127.0.0.1:8000/launcher-api/game/
    path('game/', views.launcher_game_page, name='launcher_game'),
]