from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class UserDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Пользователь", 
        related_name="devices"
    )
    session_key = models.CharField(max_length=40, verbose_name="Ключ сессии", unique=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    
    # ДОБАВИЛИ ПОЛЯ ДЛЯ ГЕОЛОКАЦИИ СЮДА
    country = models.CharField(max_length=100, default="Неизвестно", verbose_name="Страна")
    city = models.CharField(max_length=100, default="Неизвестно", verbose_name="Город")
    
    device_type = models.CharField(max_length=50, verbose_name="Тип устройства")  # PC, Mobile, Tablet
    browser = models.CharField(max_length=100, verbose_name="Браузер")
    os = models.CharField(max_length=100, verbose_name="Операционная система")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Последняя активность")

    def __str__(self):
        return f"{self.user.username} - {self.device_type} ({self.country}, {self.city})"

    class Meta:
        verbose_name = "Устройство пользователя"
        verbose_name_plural = "Устройства пользователей"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    bio = models.TextField(blank=True, verbose_name='О себе')
    country = models.CharField(max_length=100, blank=True, verbose_name='Страна')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Баланс')

    xp = models.IntegerField(default=0, verbose_name='Опыт')
    steam_level = models.IntegerField(default=0, verbose_name='Уровень')

    STATUS_CHOICES = [
        ('offline', 'Оффлайн'),
        ('online', 'Онлайн'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='Статус')

    created_at = models.DateTimeField(auto_now_add=True)

    email_verified = models.BooleanField(default=False, verbose_name='Почта подтверждена')
    verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name='Код подтверждения')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'

    def add_xp(self, amount):
        self.xp += amount

        while self.xp >= 100:
            self.xp -= 100
            self.steam_level += 1

        self.save()