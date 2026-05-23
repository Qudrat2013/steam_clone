from django.db import models
from django.contrib.auth.models import User


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принята'),
        ('declined', 'Отклонена'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username} ({self.status})'


class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_one')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_two')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f'{self.user1.username} ↔ {self.user2.username}'

    @staticmethod
    def are_friends(user_a, user_b):
        if user_a == user_b:
            return False

        u1, u2 = sorted([user_a, user_b], key=lambda u: u.id)
        return Friendship.objects.filter(user1=u1, user2=u2).exists()

    @staticmethod
    def create_friendship(user_a, user_b):
        if user_a == user_b:
            return None

        u1, u2 = sorted([user_a, user_b], key=lambda u: u.id)
        friendship, _ = Friendship.objects.get_or_create(user1=u1, user2=u2)
        return friendship