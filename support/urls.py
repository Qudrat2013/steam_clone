from django.urls import path

from . import views

urlpatterns = [
    path('', views.support_home, name='support_home'),
    # str, не slug: статьи FAQ на русском (кириллические slug)
    path('faq/<str:slug>/', views.faq_article, name='support_faq'),
    path('tickets/', views.ticket_list, name='support_tickets'),
    path('tickets/new/', views.ticket_create, name='support_ticket_create'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='support_ticket_detail'),
    path('report/', views.report_user, name='support_report'),
    path('report/<str:username>/', views.report_user, name='support_report_user'),
    path('refunds/', views.refund_list, name='support_refunds'),
    path('refunds/create/', views.refund_create, name='support_refund_create'),
    path('redeem/', views.redeem_promo, name='support_redeem'),
]
