import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail

from friends.models import Friendship, FriendRequest
from inventory.models import InventoryItem
from .models import Profile
from .forms import RegisterForm, LoginForm, ProfileForm, VerifyEmailForm


def generate_verification_code():
    return str(random.randint(100000, 999999))


def send_verification_email(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    code = generate_verification_code()
    profile.verification_code = code
    profile.save()

    send_mail(
        subject='Код подтверждения регистрации',
        message=f'Ваш код подтверждения: {code}',
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = False
            user.save()

            Profile.objects.get_or_create(user=user)
            send_verification_email(user)

            request.session['verify_user_id'] = user.id
            messages.success(request, 'Код подтверждения отправлен на вашу почту.')
            return redirect('verify_email')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    user_id = request.session.get('verify_user_id')
    if not user_id:
        messages.error(request, 'Сначала зарегистрируйтесь.')
        return redirect('register')

    user = get_object_or_404(User, id=user_id)
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = VerifyEmailForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']

            if profile.verification_code == code:
                user.is_active = True
                user.save()

                profile.email_verified = True
                profile.verification_code = ''
                profile.status = 'online'
                profile.save()

                login(request, user)
                request.session.pop('verify_user_id', None)

                messages.success(request, 'Почта успешно подтверждена.')
                return redirect('home')
            else:
                messages.error(request, 'Неверный код подтверждения.')
    else:
        form = VerifyEmailForm()

    return render(request, 'users/verify_email.html', {
        'form': form,
        'email': user.email,
    })


def resend_verification_code_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    user_id = request.session.get('verify_user_id')
    if not user_id:
        messages.error(request, 'Сначала зарегистрируйтесь.')
        return redirect('register')

    user = get_object_or_404(User, id=user_id)
    send_verification_email(user)
    messages.success(request, 'Новый код отправлен на почту.')
    return redirect('verify_email')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user:
                profile, _ = Profile.objects.get_or_create(user=user)

                if not profile.email_verified:
                    request.session['verify_user_id'] = user.id
                    messages.warning(request, 'Сначала подтвердите email.')
                    return redirect('verify_email')

                profile.status = 'online'
                profile.save()

                login(request, user)
                return redirect(request.GET.get('next', 'home'))
            else:
                form.add_error(None, 'Неверное имя пользователя или пароль')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.status = 'offline'
        profile.save()

    logout(request)
    return redirect('home')


def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    purchases = user.purchases.select_related('game').order_by('-purchased_at')
    user_achievements = user.achievements.select_related('achievement').order_by('-unlocked_at')

    showcase_items = InventoryItem.objects.filter(
        owner=user,
        show_in_profile=True
    ).select_related('item', 'item__game')[:6]

    are_friends = False
    incoming_friend_request = None
    outgoing_friend_request = None

    if request.user.is_authenticated and request.user != user:
        are_friends = Friendship.are_friends(request.user, user)

        incoming_friend_request = FriendRequest.objects.filter(
            sender=user,
            receiver=request.user,
            status='pending'
        ).first()

        outgoing_friend_request = FriendRequest.objects.filter(
            sender=request.user,
            receiver=user,
            status='pending'
        ).first()

    return render(request, 'users/profile.html', {
        'profile_user': user,
        'profile': profile,
        'purchases': purchases,
        'user_achievements': user_achievements,
        'showcase_items': showcase_items,
        'are_friends': are_friends,
        'incoming_friend_request': incoming_friend_request,
        'outgoing_friend_request': outgoing_friend_request,
    })


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён!')
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'users/edit_profile.html', {'form': form})