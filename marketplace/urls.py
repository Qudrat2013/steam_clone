from django.urls import path
from .views import (
    market_list_view,
    sell_item_view,
    buy_item_view,
    my_market_listings_view,
    cancel_listing_view,
)

urlpatterns = [
    path('', market_list_view, name='market_list'),
    path('sell/<int:inventory_item_id>/', sell_item_view, name='sell_item'),
    path('buy/<int:listing_id>/', buy_item_view, name='buy_item'),
    path('my/', my_market_listings_view, name='my_market_listings'),
    path('cancel/<int:listing_id>/', cancel_listing_view, name='cancel_listing'),
]