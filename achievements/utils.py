from .models import Achievement, UserAchievement


def give_achievement(user, name, description=''):
    achievement, _ = Achievement.objects.get_or_create(
        name=name,
        defaults={'description': description or name}
    )

    UserAchievement.objects.get_or_create(
        user=user,
        achievement=achievement
    )