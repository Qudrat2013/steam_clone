from django.urls import path
from .views import chat_list_view, chat_with_user_view, chat_messages_api, send_message_api

urlpatterns = [
    path('', chat_list_view, name='chat_list'),
    path('send/<str:username>/', send_message_api, name='chat_send_api'),
    path('<str:username>/', chat_with_user_view, name='chat_with_user'),
    path('<str:username>/messages/', chat_messages_api, name='chat_messages_api'),
]