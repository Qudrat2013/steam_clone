from django.db import models
from django.contrib.auth.models import User


class StickerPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Sticker(models.Model):
    pack = models.ForeignKey(StickerPack, on_delete=models.CASCADE, related_name='stickers')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='stickers/')
    emoji = models.CharField(max_length=10, blank=True, help_text="Эмодзи-альтернатива если нет картинки")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['pack', 'order']

    def __str__(self):
        return f'{self.pack.name} — {self.name}'


class ChatMessage(models.Model):
    MESSAGE_TYPE_TEXT = 'text'
    MESSAGE_TYPE_STICKER = 'sticker'
    MESSAGE_TYPES = [
        (MESSAGE_TYPE_TEXT, 'Текст'),
        (MESSAGE_TYPE_STICKER, 'Стикер'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default=MESSAGE_TYPE_TEXT)
    sticker = models.ForeignKey(Sticker, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username}'

    def is_sticker(self):
        return self.message_type == self.MESSAGE_TYPE_STICKER