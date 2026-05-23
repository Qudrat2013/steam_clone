from django.urls import path
from .views import wallet_view, create_balance_request

urlpatterns = [
    path('', wallet_view, name='wallet'),
    path('request/', create_balance_request, name='create_balance_request'),
]