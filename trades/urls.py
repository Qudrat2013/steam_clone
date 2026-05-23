from django.urls import path
from .views import (
    create_trade_offer_view,
    trade_detail_view,
    accept_trade_view,
    decline_trade_view,
    trade_list_view,
)

urlpatterns = [
    path('', trade_list_view, name='trade_list'),
    path('offer/<str:username>/', create_trade_offer_view, name='trade_offer'),
    path('<int:trade_id>/', trade_detail_view, name='trade_detail'),
    path('<int:trade_id>/accept/', accept_trade_view, name='accept_trade'),
    path('<int:trade_id>/decline/', decline_trade_view, name='decline_trade'),
]