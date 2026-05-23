def chat_notifications(request):
    if request.user.is_authenticated:
        unread_message_count = request.user.received_messages.filter(is_read=False).count()
        return {
            'unread_message_count': unread_message_count
        }
    return {
        'unread_message_count': 0
    }