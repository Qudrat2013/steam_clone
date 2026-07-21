from rest_framework import serializers
from django.contrib.auth.models import User

from games.models import Category, Tag, Game, Screenshot, Review
from cart.models import CartItem, Wishlist
from users.models import Profile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ['id', 'image', 'order']


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'game',
            'user',
            'username',
            'rating',
            'text',
            'hours_played',
            'created_at',
        ]
        read_only_fields = ['user', 'created_at']


class GameListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id',
            'title',
            'slug',
            'developer',
            'publisher',
            'short_description',
            'price',
            'discount',
            'discounted_price',
            'release_date',
            'category',
            'tags',
            'header_image',
            'is_featured',
            'is_active',
            'created_at',
        ]

    def get_discounted_price(self, obj):
        return str(obj.get_discounted_price())


class GameDetailSerializer(GameListSerializer):
    screenshots = ScreenshotSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta(GameListSerializer.Meta):
        fields = GameListSerializer.Meta.fields + [
            'description',
            'background_image',
            'screenshots',
            'reviews',
        ]


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'username',
            'email',
            'avatar',
            'bio',
            'country',
            'balance',
            'xp',
            'steam_level',
            'status',
            'created_at',
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'profile']


class CartItemSerializer(serializers.ModelSerializer):
    game = GameListSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.filter(is_active=True),
        source='game',
        write_only=True,
        help_text='ID игры (не id позиции корзины). Сейчас в каталоге есть игра id=10.',
    )

    class Meta:
        model = CartItem
        fields = ['id', 'game', 'game_id', 'added_at']
        read_only_fields = ['id', 'added_at']
        swagger_schema_fields = {
            'example': {'game_id': 10},
        }


class WishlistSerializer(serializers.ModelSerializer):
    game = GameListSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.filter(is_active=True),
        source='game',
        write_only=True,
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'game', 'game_id', 'added_at']
        read_only_fields = ['added_at']
