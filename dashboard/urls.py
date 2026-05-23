from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),

    path('balance-requests/', views.balance_requests_view, name='dashboard_balance_requests'),
    path('balance-requests/<int:request_id>/approve/', views.approve_balance_request_view, name='dashboard_approve_balance'),
    path('balance-requests/<int:request_id>/decline/', views.decline_balance_request_view, name='dashboard_decline_balance'),

    path('users/', views.dashboard_users_view, name='dashboard_users'),
    path('users/<int:user_id>/', views.dashboard_user_detail_view, name='dashboard_user_detail'),

    path('market/', views.dashboard_market_view, name='dashboard_market'),
    path('trades/', views.dashboard_trades_view, name='dashboard_trades'),
]