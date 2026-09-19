from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from games.models import Game


def format_play_duration(seconds):
    """Человекочитаемое время: часы, минуты или секунды."""
    seconds = max(0, int(seconds or 0))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f'{hours} ч. {minutes} мин.'
    if minutes:
        return f'{minutes} мин.' if secs == 0 else f'{minutes} мин. {secs} сек.'
    if secs:
        return f'{secs} сек.'
    return '0 мин.'


class Playtime(models.Model):
    """Наигранное время — как в Steam."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playtimes')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='playtimes')
    minutes = models.PositiveIntegerField(default=0, verbose_name='Минут сыграно')
    seconds = models.PositiveIntegerField(default=0, verbose_name='Секунд сыграно')
    last_played = models.DateTimeField(null=True, blank=True, verbose_name='Последний запуск')
    sessions = models.PositiveIntegerField(default=0, verbose_name='Сессий')

    class Meta:
        unique_together = ('user', 'game')
        verbose_name = 'Время в игре'
        verbose_name_plural = 'Время в играх'
        ordering = ['-last_played']

    def __str__(self):
        return f'{self.user.username} — {self.game.title}: {self.hours_display}'

    @property
    def total_seconds(self):
        if self.seconds:
            return self.seconds
        return int(self.minutes or 0) * 60

    @property
    def hours(self):
        return round(self.total_seconds / 3600, 1)

    @property
    def hours_display(self):
        return format_play_duration(self.total_seconds)

    def add_seconds(self, seconds, new_session=True):
        extra = max(0, int(seconds or 0))
        self.seconds = int(self.seconds or 0) + extra
        self.minutes = self.seconds // 60
        if new_session:
            self.sessions += 1
        self.last_played = timezone.now()
        self.save(update_fields=['seconds', 'minutes', 'sessions', 'last_played'])

    def add_session(self, minutes=15):
        self.add_seconds(max(1, int(minutes)) * 60, new_session=True)


class PlaySession(models.Model):
    """Одна сессия игры: от запуска до выхода. Время считается по факту."""
    SOURCE_CHOICES = [
        ('launcher', 'Лаунчер'),
        ('web', 'Сайт'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='play_sessions')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='play_sessions')
    started_at = models.DateTimeField(default=timezone.now)
    last_heartbeat = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    seconds = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='web')

    class Meta:
        verbose_name = 'Игровая сессия'
        verbose_name_plural = 'Игровые сессии'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'is_active'], name='play_sess_user_active'),
        ]

    def __str__(self):
        state = 'идёт' if self.is_active else format_play_duration(self.seconds)
        return f'{self.user.username} — {self.game.title} ({state})'

    @property
    def elapsed_seconds(self):
        if not self.is_active:
            return int(self.seconds or 0)
        end = timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))


class Activity(models.Model):
    """Лента активности (как Activity Feed)."""
    TYPE_CHOICES = [
        ('purchase', 'Покупка'),
        ('play', 'Играл'),
        ('achievement', 'Достижение'),
        ('friend', 'Друг'),
        ('review', 'Отзыв'),
        ('gift', 'Подарок'),
        ('level', 'Уровень'),
        ('status', 'Статус'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Активность'
        verbose_name_plural = 'Лента активности'

    def __str__(self):
        return f'{self.user.username}: {self.text[:40]}'


class Gift(models.Model):
    """Подарок игры другу."""
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принят'),
        ('declined', 'Отклонён'),
        ('cancelled', 'Отменён'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gifts_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gifts_received')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    message = models.CharField(max_length=250, blank=True)
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Подарок'
        verbose_name_plural = 'Подарки'

    def __str__(self):
        return f'{self.sender} → {self.receiver}: {self.game.title}'


class GameNews(models.Model):
    """Новости / обновления игры (как Steam News)."""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='news')
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_update = models.BooleanField(default=False, verbose_name='Обновление')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Новость игры'
        verbose_name_plural = 'Новости игр'

    def __str__(self):
        return self.title


class DiscoverySkip(models.Model):
    """«Не интересно» в очереди открытий."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discovery_skips')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game')


class PointsShopItem(models.Model):
    """Магазин очков Steam Points."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cost = models.PositiveIntegerField(default=100, verbose_name='Стоимость в очках')
    icon = models.CharField(max_length=40, default='fa-star', verbose_name='FontAwesome icon')
    is_active = models.BooleanField(default=True)
    reward_type = models.CharField(
        max_length=30,
        choices=[
            ('xp', 'Опыт профиля'),
            ('badge', 'Бейдж'),
            ('balance', 'Бонус на баланс'),
        ],
        default='xp',
    )
    reward_value = models.PositiveIntegerField(default=10)

    class Meta:
        verbose_name = 'Товар Points Shop'
        verbose_name_plural = 'Points Shop'

    def __str__(self):
        return f'{self.name} ({self.cost} pts)'


class PointsPurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_purchases')
    item = models.ForeignKey(PointsShopItem, on_delete=models.CASCADE)
    cost_paid = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class SaleEvent(models.Model):
    """Глобальная распродажа (Summer Sale и т.п.)."""
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=200, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    banner_color = models.CharField(max_length=20, default='#1a9fff')
    extra_discount = models.PositiveIntegerField(
        default=0,
        verbose_name='Доп. скидка % на всё',
        help_text='Накладывается поверх скидки игры (макс. 90%)',
    )

    class Meta:
        ordering = ['-starts_at']
        verbose_name = 'Распродажа'
        verbose_name_plural = 'Распродажи'

    def __str__(self):
        return self.title

    @property
    def is_live(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at


class DailyBonusClaim(models.Model):
    """История ежедневных бонусов."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_bonuses')
    claim_date = models.DateField()
    points_awarded = models.PositiveIntegerField(default=0)
    xp_awarded = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'claim_date')
        ordering = ['-claim_date']
        verbose_name = 'Daily bonus'
        verbose_name_plural = 'Daily bonuses'

    def __str__(self):
        return f'{self.user.username} — {self.claim_date} (+{self.points_awarded} pts)'


class GameRecommendation(models.Model):
    """Кэш «Вам может понравиться» (опционально)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game')
        ordering = ['-score']
