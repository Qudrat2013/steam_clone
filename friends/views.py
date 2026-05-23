from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from notifications.utils import create_notification
from .models import FriendRequest, Friendship


@login_required
def send_friend_request_view(request, username):
    receiver = get_object_or_404(User, username=username)

    if receiver == request.user:
        messages.error(request, 'Нельзя добавить в друзья самого себя.')
        return redirect('profile', username=username)

    if Friendship.are_friends(request.user, receiver):
        messages.info(request, 'Вы уже друзья.')
        return redirect('profile', username=username)

    reverse_existing = FriendRequest.objects.filter(
        sender=receiver,
        receiver=request.user,
        status='pending'
    ).first()

    if reverse_existing:
        Friendship.create_friendship(request.user, receiver)
        reverse_existing.status = 'accepted'
        reverse_existing.save()

        create_notification(
            receiver,
            'Заявка принята',
            f'{request.user.username} принял вашу заявку в друзья.',
            'friend',
            f'/users/profile/{request.user.username}/'
        )

        messages.success(request, 'Вы теперь друзья.')
        return redirect('profile', username=username)

    friend_request, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
        defaults={'status': 'pending'}
    )

    if created:
        create_notification(
            receiver,
            'Новая заявка в друзья',
            f'{request.user.username} хочет добавить вас в друзья.',
            'friend',
            f'/users/profile/{request.user.username}/'
        )
        messages.success(request, 'Заявка в друзья отправлена.')
    else:
        messages.info(request, 'Заявка уже отправлена.')

    return redirect('profile', username=username)


@login_required
def friends_list_view(request):
    query = request.GET.get('q', '').strip()

    friends = []

    for friendship in request.user.friendships_one.select_related('user2'):
        friends.append(friendship.user2)

    for friendship in request.user.friendships_two.select_related('user1'):
        friends.append(friendship.user1)

    incoming_requests = request.user.received_friend_requests.filter(
        status='pending'
    ).select_related('sender')

    search_results = []

    if query:
        search_results = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id)[:20]

    return render(request, 'friends/friends_list.html', {
        'friends': friends,
        'incoming_requests': incoming_requests,
        'search_results': search_results,
        'query': query,
    })


@login_required
def accept_friend_request_view(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        receiver=request.user,
        status='pending'
    )

    Friendship.create_friendship(friend_request.sender, friend_request.receiver)
    friend_request.status = 'accepted'
    friend_request.save()

    request.user.profile.add_xp(10)
    friend_request.sender.profile.add_xp(10)

    create_notification(
        friend_request.sender,
        'Заявка принята',
        f'{request.user.username} принял вашу заявку в друзья.',
        'friend',
        f'/users/profile/{request.user.username}/'
    )

    messages.success(request, 'Заявка в друзья принята.')
    return redirect('friends_list')


@login_required
def decline_friend_request_view(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        receiver=request.user,
        status='pending'
    )

    friend_request.status = 'declined'
    friend_request.save()

    create_notification(
        friend_request.sender,
        'Заявка отклонена',
        f'{request.user.username} отклонил вашу заявку в друзья.',
        'friend',
        f'/users/profile/{request.user.username}/'
    )

    messages.info(request, 'Заявка отклонена.')
    return redirect('friends_list')


@login_required
def remove_friend_view(request, username):
    friend = get_object_or_404(User, username=username)

    friendship = Friendship.objects.filter(
        Q(user1=request.user, user2=friend) |
        Q(user1=friend, user2=request.user)
    ).first()

    if friendship:
        friendship.delete()

        create_notification(
            friend,
            'Удаление из друзей',
            f'{request.user.username} удалил вас из друзей.',
            'friend',
            f'/users/profile/{request.user.username}/'
        )

        messages.success(request, f'{friend.username} удалён из друзей.')
    else:
        messages.error(request, 'Этот пользователь не у вас в друзьях.')

    return redirect('friends_list')