from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from cart.models import Purchase


@csrf_exempt
def login_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()

    user = authenticate(username=username, password=password)

    if not user:
        return JsonResponse({'error': 'Неверный логин или пароль'}, status=401)

    if not user.is_active:
        return JsonResponse({'error': 'Аккаунт не активен'}, status=403)

    return JsonResponse({
        'success': True,
        'user_id': user.id,
        'username': user.username,
    })


def library_api(request):
    user_id = request.GET.get('user_id')

    user = User.objects.filter(id=user_id, is_active=True).first()

    if not user:
        return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    purchases = Purchase.objects.filter(user=user).select_related('game')

    games = []

    for purchase in purchases:
        game = purchase.game

        file_url = ''
        if game.game_file:
            file_url = request.build_absolute_uri(game.game_file.url)

        image_url = ''
        if game.header_image:
            image_url = request.build_absolute_uri(game.header_image.url)

        games.append({
            'id': game.id,
            'title': game.title,
            'file_url': file_url,
            'image_url': image_url,
        })

    return JsonResponse({
        'success': True,
        'games': games,
    })