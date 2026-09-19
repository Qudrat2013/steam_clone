from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def copy_minutes_to_seconds(apps, schema_editor):
    Playtime = apps.get_model('steamplus', 'Playtime')
    for pt in Playtime.objects.all().iterator():
        minutes = pt.minutes or 0
        if not pt.seconds:
            pt.seconds = minutes * 60
            pt.save(update_fields=['seconds'])


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_game_game_file'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('steamplus', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='playtime',
            name='seconds',
            field=models.PositiveIntegerField(default=0, verbose_name='Секунд сыграно'),
        ),
        migrations.CreateModel(
            name='PlaySession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_heartbeat', models.DateTimeField(default=django.utils.timezone.now)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('seconds', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('source', models.CharField(choices=[('launcher', 'Лаунчер'), ('web', 'Сайт')], default='web', max_length=20)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='play_sessions', to='games.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='play_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Игровая сессия',
                'verbose_name_plural': 'Игровые сессии',
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='playsession',
            index=models.Index(fields=['user', 'is_active'], name='play_sess_user_active'),
        ),
        migrations.RunPython(copy_minutes_to_seconds, migrations.RunPython.noop),
    ]
