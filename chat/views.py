from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from friends.models import Friendship
from .models import ChatMessage, Sticker, StickerPack


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
    ).select_related('sticker', 'sticker__pack').order_by('created_at')

    ChatMessage.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    sticker_packs = StickerPack.objects.prefetch_related('stickers').all()

    if request.method == 'POST':
        msg_type = request.POST.get('message_type', 'text')

        if msg_type == 'sticker':
            sticker_id = request.POST.get('sticker_id')
            if sticker_id:
                sticker = get_object_or_404(Sticker, id=sticker_id)
                ChatMessage.objects.create(
                    sender=request.user,
                    receiver=other_user,
                    message_type='sticker',
                    sticker=sticker,
                )
        else:
            text = request.POST.get('text', '').strip()
            if text:
                ChatMessage.objects.create(
                    sender=request.user,
                    receiver=other_user,
                    text=text,
                    message_type='text',
                )

        return redirect('chat_with_user', username=other_user.username)

    return render(request, 'chat/chat.html', {
        'other_user': other_user,
        'messages_list': messages_qs,
        'sticker_packs': sticker_packs,
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

    last_id = request.GET.get('last_id', 0)
    messages_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).filter(id__gt=last_id).select_related('sticker').order_by('created_at')

    data = []
    for msg in messages_qs:
        item = {
            'id': msg.id,
            'sender': msg.sender.username,
            'is_mine': msg.sender_id == request.user.id,
            'created_at': msg.created_at.strftime('%H:%M'),
            'message_type': msg.message_type,
            'text': msg.text,
            'sticker_url': msg.sticker.image.url if msg.sticker and msg.sticker.image else None,
            'sticker_name': msg.sticker.name if msg.sticker else None,
        }
        data.append(item)

    return JsonResponse({'messages': data})


@login_required
def send_message_api(request, username):
    """AJAX endpoint для отправки сообщений и стикеров."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    other_user = get_object_or_404(User, username=username)

    if not Friendship.are_friends(request.user, other_user):
        return JsonResponse({'error': 'forbidden'}, status=403)

    msg_type = request.POST.get('message_type', 'text')

    if msg_type == 'sticker':
        sticker_id = request.POST.get('sticker_id')
        if not sticker_id:
            return JsonResponse({'error': 'sticker_id required'}, status=400)
        sticker = get_object_or_404(Sticker, id=sticker_id)
        msg = ChatMessage.objects.create(
            sender=request.user,
            receiver=other_user,
            message_type='sticker',
            sticker=sticker,
        )
        return JsonResponse({
            'id': msg.id,
            'sender': msg.sender.username,
            'is_mine': True,
            'created_at': msg.created_at.strftime('%H:%M'),
            'message_type': 'sticker',
            'sticker_url': sticker.image.url if sticker.image else None,
            'sticker_name': sticker.name,
        })
    else:
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'empty message'}, status=400)
        msg = ChatMessage.objects.create(
            sender=request.user,
            receiver=other_user,
            text=text,
            message_type='text',
        )
        return JsonResponse({
            'id': msg.id,
            'sender': msg.sender.username,
            'is_mine': True,
            'created_at': msg.created_at.strftime('%H:%M'),
            'message_type': 'text',
            'text': msg.text,
        })


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