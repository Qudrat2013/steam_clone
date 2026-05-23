from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from .models import Game, Category, Tag, Review


def home(request):
    featured_games = Game.objects.filter(is_featured=True, is_active=True)[:5]
    new_releases = Game.objects.filter(is_active=True).order_by('-release_date')[:12]
    top_sellers = Game.objects.filter(is_active=True)[:8]
    categories = Category.objects.all()

    context = {
        'featured_games': featured_games,
        'new_releases': new_releases,
        'top_sellers': top_sellers,
        'categories': categories,
    }
    return render(request, 'games/home.html', context)


def game_list(request):
    games = Game.objects.filter(is_active=True)
    categories = Category.objects.all()
    tags = Tag.objects.all()

    # Поиск
    query = request.GET.get('q')
    if query:
        games = games.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(developer__icontains=query)
        )

    # Фильтр по категории
    category_slug = request.GET.get('category')
    if category_slug:
        games = games.filter(category__slug=category_slug)

    # Фильтр по тегу
    tag_slug = request.GET.get('tag')
    if tag_slug:
        games = games.filter(tags__slug=tag_slug)

    # Фильтр по цене
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        games = games.filter(price__gte=price_min)
    if price_max:
        games = games.filter(price__lte=price_max)

    # Сортировка
    sort = request.GET.get('sort', '-created_at')
    games = games.order_by(sort)

    context = {
        'games': games,
        'categories': categories,
        'tags': tags,
        'query': query,
    }
    return render(request, 'games/game_list.html', context)


def game_detail(request, slug):
    game = get_object_or_404(Game, slug=slug, is_active=True)
    screenshots = game.screenshots.all()
    reviews = game.reviews.all().order_by('-created_at')
    
    # Рейтинг
    positive = reviews.filter(rating=True).count()
    total = reviews.count()
    rating_percent = int((positive / total) * 100) if total > 0 else 0

    # Проверка: купил ли пользователь игру
    user_owns = False
    user_review = None
    if request.user.is_authenticated:
        from cart.models import Purchase
        user_owns = Purchase.objects.filter(user=request.user, game=game).exists()
        try:
            user_review = Review.objects.get(game=game, user=request.user)
        except Review.DoesNotExist:
            pass

    # Похожие игры
    similar_games = Game.objects.filter(
        category=game.category, is_active=True
    ).exclude(id=game.id)[:4]

    context = {
        'game': game,
        'screenshots': screenshots,
        'reviews': reviews,
        'rating_percent': rating_percent,
        'total_reviews': total,
        'user_owns': user_owns,
        'user_review': user_review,
        'similar_games': similar_games,
    }
    return render(request, 'games/game_detail.html', context)


@login_required
def add_review(request, slug):
    game = get_object_or_404(Game, slug=slug)
    if request.method == 'POST':
        rating = request.POST.get('rating') == 'positive'
        text = request.POST.get('text')
        Review.objects.update_or_create(
            game=game, user=request.user,
            defaults={'rating': rating, 'text': text}
        )
        messages.success(request, 'Отзыв добавлен!')
    return redirect('game_detail', slug=slug)
from django.http import FileResponse, Http404
from cart.models import Purchase
from django.contrib.auth.decorators import login_required


@login_required
def download_game(request, game_id):
    purchase = Purchase.objects.filter(
        user=request.user,
        game_id=game_id
    ).select_related('game').first()

    if not purchase:
        raise Http404('У вас нет этой игры')

    game = purchase.game

    if not game.game_file:
        raise Http404('Файл игры не найден')

    return FileResponse(
        game.game_file.open('rb'),
        as_attachment=True,
        filename=game.game_file.name.split('/')[-1]
    )