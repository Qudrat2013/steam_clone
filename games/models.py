from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, verbose_name='Тег')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Game(models.Model):
    game_file = models.FileField(upload_to='games/files/', blank=True, null=True, verbose_name='Файл игры (.exe)')
    title = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(unique=True)
    developer = models.CharField(max_length=200, verbose_name='Разработчик')
    publisher = models.CharField(max_length=200, verbose_name='Издатель')
    description = models.TextField(verbose_name='Описание')
    short_description = models.CharField(max_length=300, verbose_name='Краткое описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    discount = models.IntegerField(default=0, verbose_name='Скидка %')
    release_date = models.DateField(verbose_name='Дата выхода')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name='Категория')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='Теги')
    header_image = models.ImageField(upload_to='games/headers/', verbose_name='Заглавное изображение')
    background_image = models.ImageField(upload_to='games/backgrounds/', blank=True, verbose_name='Фон')
    is_featured = models.BooleanField(default=False, verbose_name='На главной')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('game_detail', kwargs={'slug': self.slug})

    def get_discounted_price(self):
        if self.discount > 0:
            discounted = self.price * (
                Decimal('1') - (Decimal(str(self.discount)) / Decimal('100'))
            )
            return discounted.quantize(Decimal('0.01'))
        return self.price


class Screenshot(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='screenshots')
    image = models.ImageField(upload_to='games/screenshots/')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']


class Review(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.BooleanField(verbose_name='Рекомендую')
    text = models.TextField(verbose_name='Отзыв')
    created_at = models.DateTimeField(auto_now_add=True)
    hours_played = models.IntegerField(default=0, verbose_name='Часов в игре')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('game', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.game.title}'