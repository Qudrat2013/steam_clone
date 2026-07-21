from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from games.models import Category, Tag, Game, Review
from cart.models import CartItem, Wishlist
from .serializers import (
    CategorySerializer,
    TagSerializer,
    GameListSerializer,
    GameDetailSerializer,
    ReviewSerializer,
    UserSerializer,
    ProfileSerializer,
    CartItemSerializer,
    WishlistSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Список и детали категорий игр."""

    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Список и детали тегов."""

    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """Каталог игр: список, детали, избранные, поиск."""

    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        qs = (
            Game.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('tags', 'screenshots', 'reviews__user')
        )
        category = self.request.query_params.get('category')
        tag = self.request.query_params.get('tag')
        search = self.request.query_params.get('search')
        featured = self.request.query_params.get('featured')
        ordering = self.request.query_params.get('ordering', '-created_at')

        if category:
            qs = qs.filter(category__slug=category)
        if tag:
            qs = qs.filter(tags__slug=tag)
        if search:
            qs = qs.filter(title__icontains=search)
        if featured in ('1', 'true', 'True'):
            qs = qs.filter(is_featured=True)

        allowed = {
            'price', '-price', 'title', '-title',
            'release_date', '-release_date', 'created_at', '-created_at',
        }
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GameDetailSerializer
        return GameListSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='slug категории'),
            openapi.Parameter('tag', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='slug тега'),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='поиск по названию'),
            openapi.Parameter('featured', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, description='только featured'),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='price, -price, title, release_date, created_at',
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Игры, отмеченные как featured."""
        qs = self.get_queryset().filter(is_featured=True)[:12]
        serializer = GameListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class ReviewViewSet(mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """Отзывы к играм."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'game').order_by('-created_at')
        game = self.request.query_params.get('game')
        if game:
            qs = qs.filter(game__slug=game) if not game.isdigit() else qs.filter(game_id=game)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartViewSet(viewsets.ModelViewSet):
    """
    Корзина текущего пользователя.

    **Как пользоваться:**
    1. Авторизуйся (Token или session login)
    2. `GET /api/cart/` — список позиций (смотри поле `id`)
    3. `POST /api/cart/` с body `{"game_id": 10}` — добавить игру
    4. `DELETE /api/cart/{id}/` — удалить **id позиции из корзины**, не id игры

    404 = такой позиции в *твоей* корзине нет (пустая корзина или неверный id).
    """

    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return CartItem.objects.none()
        return (
            CartItem.objects.filter(user=self.request.user)
            .select_related('game', 'game__category')
            .prefetch_related('game__tags')
            .order_by('-added_at')
        )

    def create(self, request, *args, **kwargs):
        game = request.data.get('game_id')
        if game is None:
            return Response(
                {'detail': 'Передай game_id (id игры). Пример: {"game_id": 10}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = CartItem.objects.filter(user=request.user, game_id=game).first()
        if existing:
            serializer = self.get_serializer(existing)
            return Response(
                {
                    'detail': 'Игра уже в корзине',
                    'item': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        item = self.get_queryset().filter(pk=pk).first()
        if not item:
            my_ids = list(self.get_queryset().values_list('id', flat=True))
            return Response(
                {
                    'detail': f'В твоей корзине нет позиции id={pk}.',
                    'hint': 'Сначала GET /api/cart/ и бери id оттуда. Либо POST {"game_id": 10} чтобы добавить.',
                    'your_cart_item_ids': my_ids,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'], url_path='clear')
    def clear(self, request):
        """Очистить всю корзину."""
        deleted, _ = self.get_queryset().delete()
        return Response({'deleted': deleted})


class WishlistViewSet(viewsets.ModelViewSet):
    """
    Список желаемого.

    `DELETE /api/wishlist/{id}/` — id **позиции wishlist**, не id игры.
    Добавить: `POST /api/wishlist/` body `{"game_id": 10}`.
    """

    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Wishlist.objects.none()
        return (
            Wishlist.objects.filter(user=self.request.user)
            .select_related('game', 'game__category')
            .prefetch_related('game__tags')
            .order_by('-added_at')
        )

    def create(self, request, *args, **kwargs):
        game = request.data.get('game_id')
        if game is None:
            return Response(
                {'detail': 'Передай game_id. Пример: {"game_id": 10}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = Wishlist.objects.filter(user=request.user, game_id=game).first()
        if existing:
            serializer = self.get_serializer(existing)
            return Response({'detail': 'Уже в wishlist', 'item': serializer.data})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        item = self.get_queryset().filter(pk=pk).first()
        if not item:
            my_ids = list(self.get_queryset().values_list('id', flat=True))
            return Response(
                {
                    'detail': f'В wishlist нет позиции id={pk}.',
                    'your_wishlist_item_ids': my_ids,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='get',
    operation_description='Профиль текущего пользователя',
    responses={200: UserSerializer},
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    serializer = UserSerializer(request.user, context={'request': request})
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    operation_description='Получить auth token (логин)',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
        },
    ),
    responses={
        200: openapi.Response(
            'OK',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'token': openapi.Schema(type=openapi.TYPE_STRING),
                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        )
    },
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_api(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'detail': 'Неверный логин или пароль'}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user_id': user.id, 'username': user.username})


@swagger_auto_schema(
    method='post',
    operation_description='Регистрация нового пользователя',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
        },
    ),
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_api(request):
    username = (request.data.get('username') or '').strip()
    email = (request.data.get('email') or '').strip()
    password = request.data.get('password') or ''

    if not username or not password:
        return Response({'detail': 'username и password обязательны'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'detail': 'Пользователь уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)
    from users.models import Profile
    Profile.objects.get_or_create(user=user)
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
        },
        status=status.HTTP_201_CREATED,
    )

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

