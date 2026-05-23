def trade_notifications(request):
    if request.user.is_authenticated:
        pending_trade_count = request.user.received_trade_offers.filter(status='pending').count()
        return {
            'pending_trade_count': pending_trade_count
        }
    return {
        'pending_trade_count': 0
    }