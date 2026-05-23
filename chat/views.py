from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from friends.models import Friendship
from .models import ChatMessage


@login_required
def chat_with_user_view(request, username):
    other_user = get_object_or_404(User, username=username)

    if other_user == request.user:
        messages.error(request, 'Нельзя открыть чат с самим собой.')
        return redirect('profile', username=username)

    if not Friendship.are_friends(request.user, other_user):
        messages.error(request, 'Общение доступно только между друзьями.')
        return redirect('profile', username=username)

    messages_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')

    ChatMessage.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            ChatMessage.objects.create(
                sender=request.user,
                receiver=other_user,
                text=text
            )
            return redirect('chat_with_user', username=other_user.username)

    return render(request, 'chat/chat.html', {
        'other_user': other_user,
        'messages_list': messages_qs,
    })


@login_required
def chat_messages_api(request, username):
    other_user = get_object_or_404(User, username=username)

    if not Friendship.are_friends(request.user, other_user):
        return JsonResponse({'error': 'forbidden'}, status=403)

    ChatMessage.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    messages_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')

    data = []
    for msg in messages_qs:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'text': msg.text,
            'is_mine': msg.sender_id == request.user.id,
            'created_at': msg.created_at.strftime('%H:%M'),
        })

    return JsonResponse({'messages': data})


@login_required
def chat_list_view(request):
    friend_ids = set()

    for friendship in request.user.friendships_one.select_related('user2'):
        friend_ids.add(friendship.user2.id)

    for friendship in request.user.friendships_two.select_related('user1'):
        friend_ids.add(friendship.user1.id)

    friends = User.objects.filter(id__in=friend_ids)

    return render(request, 'chat/chat_list.html', {
        'friends': friends,
    })