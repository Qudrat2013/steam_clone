from django.urls import path

from . import client_api, views

urlpatterns = [
    # Страница управления играми (веб): http://127.0.0.1:8000/launcher-api/game/
    path('game/', views.launcher_game_page, name='launcher_game'),
    # Скачивание лаунчера: http://127.0.0.1:8000/launcher-api/download/
    path('download/', views.download_launcher, name='download_launcher'),
    # ---- API нативного лаунчера (Authorization: Token <key>) ----
    path('client/library/', client_api.client_library, name='client_library'),
    path('client/play/start/', client_api.client_play_start, name='client_play_start'),
    path('client/play/heartbeat/', client_api.client_play_heartbeat, name='client_play_heartbeat'),
    path('client/play/end/', client_api.client_play_end, name='client_play_end'),
    path('client/store/', client_api.client_store, name='client_store'),
    path('client/buy/', client_api.client_buy, name='client_buy'),
    path('client/chat/dialogs/', client_api.client_chat_dialogs, name='client_chat_dialogs'),
    path('client/chat/messages/', client_api.client_chat_messages, name='client_chat_messages'),
    path('client/chat/send/', client_api.client_chat_send, name='client_chat_send'),
    path('client/users/', client_api.client_users, name='client_users'),
    path('client/wishlist/', client_api.client_wishlist_toggle, name='client_wishlist'),
    path('client/bonus/', client_api.client_bonus, name='client_bonus'),
    path('client/register/', client_api.client_register, name='client_register'),
    path('client/profile/', client_api.client_profile, name='client_profile'),
    path('client/ping/', client_api.client_ping, name='client_ping'),
    path('client/qr/create/', client_api.client_qr_create, name='client_qr_create'),
    path('client/qr/status/', client_api.client_qr_status, name='client_qr_status'),
    path('client/qr/img/', client_api.client_qr_img, name='client_qr_img'),
    path('qr/<str:code>/', client_api.qr_approve_page, name='qr_approve'),
]
