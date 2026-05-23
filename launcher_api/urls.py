from django.urls import path
from .views import login_api, library_api

urlpatterns = [
    path('login/', login_api, name='launcher_login_api'),
    path('library/', library_api, name='launcher_library_api'),
]