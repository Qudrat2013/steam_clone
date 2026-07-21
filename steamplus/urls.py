from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='discovery_queue', permanent=False), name='steamplus_home'),
    path('discovery/', views.discovery_queue, name='discovery_queue'),
    path('discovery/<int:game_id>/', views.discovery_action, name='discovery_action'),
    path('activity/', views.activity_feed, name='activity_feed'),
    path('play/<int:game_id>/', views.play_game, name='play_game'),
    path('gift/<int:game_id>/', views.gift_game, name='gift_game'),
    path('gifts/', views.gifts_inbox, name='gifts_inbox'),
    path('gifts/<int:gift_id>/respond/', views.gift_respond, name='gift_respond'),
    path('points/', views.points_shop, name='points_shop'),
    path('points/buy/<int:item_id>/', views.buy_points_item, name='buy_points_item'),
    path('status/', views.set_status, name='set_status'),
    path('search/suggest/', views.search_suggest, name='search_suggest'),
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.game_news, name='game_news'),
    path('recent/', views.recently_played, name='recently_played'),
    path('friends-online/', views.friends_playing, name='friends_playing'),
    path('daily/', views.daily_bonus, name='daily_bonus'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('for-you/', views.recommendations, name='recommendations'),
    path('random/', views.random_game, name='random_game'),
    path('sales/', views.sales_hub, name='sales_hub'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
    path('compare/', views.compare_friends_library, name='compare_friends'),
]
