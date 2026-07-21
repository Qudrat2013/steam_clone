from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),

    # Balance
    path('balance-requests/', views.balance_requests_view, name='dashboard_balance_requests'),
    path('balance-requests/<int:request_id>/approve/', views.approve_balance_request_view, name='dashboard_approve_balance'),
    path('balance-requests/<int:request_id>/decline/', views.decline_balance_request_view, name='dashboard_decline_balance'),

    # Users
    path('users/', views.dashboard_users_view, name='dashboard_users'),
    path('users/<int:user_id>/', views.dashboard_user_detail_view, name='dashboard_user_detail'),

    # Market / trades / purchases
    path('market/', views.dashboard_market_view, name='dashboard_market'),
    path('market/<int:listing_id>/cancel/', views.dashboard_market_cancel, name='dashboard_market_cancel'),
    path('trades/', views.dashboard_trades_view, name='dashboard_trades'),
    path('purchases/', views.dashboard_purchases_view, name='dashboard_purchases'),

    # Games
    path('games/', views.dashboard_games_view, name='dashboard_games'),
    path('games/new/', views.dashboard_game_edit, name='dashboard_game_new'),
    path('games/<int:game_id>/', views.dashboard_game_edit, name='dashboard_game_edit'),
    path('games/<int:game_id>/toggle/', views.dashboard_game_toggle, name='dashboard_game_toggle'),

    # Support tickets
    path('tickets/', views.dashboard_tickets_view, name='dashboard_tickets'),
    path('tickets/<int:ticket_id>/', views.dashboard_ticket_detail, name='dashboard_ticket_detail'),

    # Reports & bans
    path('reports/', views.dashboard_reports_view, name='dashboard_reports'),
    path('reports/<int:report_id>/', views.dashboard_report_detail, name='dashboard_report_detail'),
    path('bans/', views.dashboard_bans_view, name='dashboard_bans'),
    path('bans/<int:ban_id>/lift/', views.dashboard_ban_lift, name='dashboard_ban_lift'),

    # Refunds
    path('refunds/', views.dashboard_refunds_view, name='dashboard_refunds'),
    path('refunds/<int:refund_id>/', views.dashboard_refund_action, name='dashboard_refund_action'),

    # Reviews
    path('reviews/', views.dashboard_reviews_view, name='dashboard_reviews'),
    path('reviews/<int:review_id>/delete/', views.dashboard_review_delete, name='dashboard_review_delete'),

    # Promos
    path('promos/', views.dashboard_promos_view, name='dashboard_promos'),
    path('promos/<int:promo_id>/toggle/', views.dashboard_promo_toggle, name='dashboard_promo_toggle'),

    # Broadcast
    path('broadcast/', views.dashboard_broadcast_view, name='dashboard_broadcast'),

    # Sales & news
    path('sales/', views.dashboard_sales_view, name='dashboard_sales'),
    path('sales/<int:sale_id>/toggle/', views.dashboard_sale_toggle, name='dashboard_sale_toggle'),
    path('news/', views.dashboard_news_view, name='dashboard_news'),

    # FAQ
    path('faq/', views.dashboard_faq_view, name='dashboard_faq'),
    path('faq/<int:article_id>/delete/', views.dashboard_faq_delete, name='dashboard_faq_delete'),

    # Items
    path('items/', views.dashboard_items_view, name='dashboard_items'),

    # System
    path('audit/', views.dashboard_audit_view, name='dashboard_audit'),
    path('devices/', views.dashboard_devices_view, name='dashboard_devices'),
    path('stats/', views.dashboard_stats_view, name='dashboard_stats'),
]
