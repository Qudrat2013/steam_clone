from django.urls import path
from .views import (
    send_friend_request_view,
    friends_list_view,
    accept_friend_request_view,
    decline_friend_request_view,
    remove_friend_view,
)

urlpatterns = [
    path('', friends_list_view, name='friends_list'),
    path('add/<str:username>/', send_friend_request_view, name='send_friend_request'),
    path('remove/<str:username>/', remove_friend_view, name='remove_friend'),
    path('accept/<int:request_id>/', accept_friend_request_view, name='accept_friend_request'),
    path('decline/<int:request_id>/', decline_friend_request_view, name='decline_friend_request'),
]