from django.urls import path
from . import views
 
app_name = 'groups'
 
urlpatterns = [
    path('', views.group_list, name='list'),
    path('create/', views.group_create, name='create'),
    path('<int:pk>/', views.group_detail, name='detail'),
    path('<int:pk>/join/', views.group_join, name='join'),
    path('<int:pk>/leave/', views.group_leave, name='leave'),
    path('<int:pk>/forum/', views.group_forum, name='forum'),
    path('<int:pk>/forum/post/', views.group_post_create, name='post_create'),
    path('<int:pk>/forum/<int:post_pk>/', views.group_post_detail, name='post_detail'),
    path('<int:pk>/chat/', views.group_chat, name='chat'),
    path('<int:pk>/chat/send/', views.group_chat_send, name='chat_send'),
    path('<int:pk>/chat/messages/', views.group_chat_messages, name='chat_messages'),
]
 