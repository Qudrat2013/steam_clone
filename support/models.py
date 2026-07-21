from django.conf import settings
from django.db import models
from django.utils import timezone


class SupportTicket(models.Model):
    """Тикет поддержки — как Steam Support."""
    CATEGORY_CHOICES = [
        ('account', 'Аккаунт и безопасность'),
        ('payment', 'Платежи и кошелёк'),
        ('purchase', 'Покупки и возвраты'),
        ('game', 'Проблемы с игрой'),
        ('trade', 'Обмены'),
        ('market', 'Торговая площадка'),
        ('inventory', 'Инвентарь'),
        ('friends', 'Друзья и чат'),
        ('report', 'Жалоба'),
        ('other', 'Другое'),
    ]
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('pending', 'Ожидает ответа'),
        ('in_progress', 'В работе'),
        ('waiting_user', 'Ждёт пользователя'),
        ('resolved', 'Решён'),
        ('closed', 'Закрыт'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    subject = models.CharField(max_length=200, verbose_name='Тема')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name='Агент',
    )
    related_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Тикет поддержки'
        verbose_name_plural = 'Тикеты поддержки'

    def __str__(self):
        return f'#{self.id} {self.subject} ({self.user.username})'

    @property
    def is_open(self):
        return self.status not in ('resolved', 'closed')

    def mark_closed(self, status='closed'):
        self.status = status
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class TicketMessage(models.Model):
    """Сообщение в тикете."""
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(verbose_name='Сообщение')
    is_staff_reply = models.BooleanField(default=False, verbose_name='Ответ поддержки')
    is_internal = models.BooleanField(default=False, verbose_name='Внутренняя заметка')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение тикета'
        verbose_name_plural = 'Сообщения тикетов'

    def __str__(self):
        return f'Ticket #{self.ticket_id} — {self.author.username}'


class UserReport(models.Model):
    """Жалоба на пользователя / контент."""
    TARGET_CHOICES = [
        ('user', 'Пользователь'),
        ('review', 'Отзыв'),
        ('market', 'Лот маркета'),
        ('chat', 'Сообщение чата'),
        ('group', 'Группа'),
        ('trade', 'Обмен'),
        ('other', 'Другое'),
    ]
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('scam', 'Мошенничество'),
        ('harassment', 'Оскорбления / травля'),
        ('cheating', 'Читы / нарушения'),
        ('inappropriate', 'Неприемлемый контент'),
        ('impersonation', 'Самозванец'),
        ('other', 'Другое'),
    ]
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('reviewing', 'Проверяется'),
        ('action_taken', 'Приняты меры'),
        ('dismissed', 'Отклонена'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_made',
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_against',
    )
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default='user')
    target_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID объекта')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    description = models.TextField(verbose_name='Описание')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True, verbose_name='Заметка модератора')
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_handled',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'

    def __str__(self):
        return f'Жалоба #{self.id} от {self.reporter.username}'


class UserBan(models.Model):
    """Бан / VAC-style ограничения."""
    BAN_TYPE_CHOICES = [
        ('full', 'Полный бан аккаунта'),
        ('trade', 'Бан обменов'),
        ('market', 'Бан маркета'),
        ('chat', 'Бан чата'),
        ('community', 'Бан сообщества'),
        ('temp', 'Временный бан'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bans',
    )
    banned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bans_issued',
    )
    ban_type = models.CharField(max_length=20, choices=BAN_TYPE_CHOICES, default='full')
    reason = models.TextField(verbose_name='Причина')
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name='До (пусто = навсегда)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Бан'
        verbose_name_plural = 'Баны'

    def __str__(self):
        return f'{self.user.username} — {self.get_ban_type_display()}'

    @property
    def is_expired(self):
        if not self.is_active:
            return True
        if self.ends_at and timezone.now() > self.ends_at:
            return True
        return False

    def lift(self):
        self.is_active = False
        self.save(update_fields=['is_active'])


class FAQCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, allow_unicode=True)
    icon = models.CharField(max_length=40, default='fa-question-circle')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Категория FAQ'
        verbose_name_plural = 'Категории FAQ'

    def __str__(self):
        return self.name


class FAQArticle(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='articles')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, allow_unicode=True)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    views = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Статья FAQ'
        verbose_name_plural = 'Статьи FAQ'

    def __str__(self):
        return self.title


class PromoCode(models.Model):
    """Промокоды / подарочные коды."""
    REWARD_CHOICES = [
        ('balance', 'Баланс'),
        ('points', 'Steam Points'),
        ('xp', 'Опыт'),
        ('game', 'Игра'),
        ('discount', 'Скидка %'),
    ]

    code = models.CharField(max_length=40, unique=True, verbose_name='Код')
    description = models.CharField(max_length=200, blank=True)
    reward_type = models.CharField(max_length=20, choices=REWARD_CHOICES, default='balance')
    reward_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_codes',
    )
    max_uses = models.PositiveIntegerField(default=1, verbose_name='Макс. активаций')
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_codes_created',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.used_count >= self.max_uses:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True


class PromoRedemption(models.Model):
    promo = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='redemptions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_redemptions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('promo', 'user')
        ordering = ['-created_at']
        verbose_name = 'Активация промокода'
        verbose_name_plural = 'Активации промокодов'

    def __str__(self):
        return f'{self.user.username} — {self.promo.code}'


class RefundRequest(models.Model):
    """Запрос на возврат покупки (как Steam Refund)."""
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрен'),
        ('declined', 'Отклонён'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='refund_requests')
    purchase = models.ForeignKey(
        'cart.Purchase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund_requests',
    )
    game_title = models.CharField(max_length=200, blank=True, verbose_name='Игра (снимок)')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма возврата')
    reason = models.TextField(verbose_name='Причина')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds_handled',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Запрос на возврат'
        verbose_name_plural = 'Запросы на возврат'

    def __str__(self):
        title = self.game_title or (self.purchase.game.title if self.purchase_id else '?')
        return f'Refund #{self.id} — {self.user.username} — {title}'


class AdminAuditLog(models.Model):
    """Журнал действий админов."""
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Аудит-лог'
        verbose_name_plural = 'Аудит-логи'

    def __str__(self):
        return f'{self.admin} — {self.action} @ {self.created_at:%Y-%m-%d %H:%M}'


class BroadcastMessage(models.Model):
    """Массовое уведомление всем / группе пользователей."""
    TARGET_CHOICES = [
        ('all', 'Всем'),
        ('staff', 'Только staff'),
        ('active', 'Активным (за 30 дней)'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='broadcasts_sent',
    )
    sent_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'

    def __str__(self):
        return self.title
