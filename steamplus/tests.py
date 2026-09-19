from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from cart.models import Purchase
from games.models import Game
from steamplus.models import PlaySession, Playtime, format_play_duration
from steamplus.utils import end_play_session, start_play_session


class PlaytimeTrackingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='player', password='pass12345')
        self.game = Game.objects.create(
            title='Test Game',
            slug='test-game',
            developer='Dev',
            publisher='Pub',
            description='desc',
            short_description='short',
            price=0,
            release_date='2024-01-01',
        )
        Purchase.objects.create(user=self.user, game=self.game, price_paid=0)

    def test_format_duration(self):
        self.assertEqual(format_play_duration(0), '0 мин.')
        self.assertEqual(format_play_duration(12), '12 сек.')
        self.assertEqual(format_play_duration(90), '1 мин. 30 сек.')
        self.assertEqual(format_play_duration(3661), '1 ч. 1 мин.')

    def test_start_and_end_records_elapsed_seconds(self):
        session = start_play_session(self.user, self.game, source='web')
        session.started_at = timezone.now() - timedelta(minutes=12, seconds=40)
        session.last_heartbeat = timezone.now()
        session.save(update_fields=['started_at', 'last_heartbeat'])

        ended = end_play_session(self.user, session_id=session.id)
        self.assertFalse(ended.is_active)
        self.assertGreaterEqual(ended.seconds, 12 * 60)
        self.assertLess(ended.seconds, 13 * 60)

        pt = Playtime.objects.get(user=self.user, game=self.game)
        self.assertEqual(pt.seconds, ended.seconds)
        self.assertEqual(pt.minutes, ended.seconds // 60)
        self.assertEqual(pt.sessions, 1)
        self.assertIn('мин.', pt.hours_display)

    def test_play_api_does_not_add_fake_30_minutes(self):
        self.client.login(username='player', password='pass12345')
        res = self.client.post(
            f'/plus/play/{self.game.id}/start/',
            data='{"source":"web"}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload['playing'])
        self.assertEqual(payload['game_id'], self.game.id)

        session = PlaySession.objects.get(id=payload['session_id'])
        session.started_at = timezone.now() - timedelta(minutes=7)
        session.last_heartbeat = timezone.now()
        session.save(update_fields=['started_at', 'last_heartbeat'])

        end = self.client.post(
            f'/plus/play/{self.game.id}/end/',
            data=f'{{"session_id": {session.id}}}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(end.status_code, 200)
        data = end.json()
        self.assertFalse(data['playing'])
        self.assertGreaterEqual(data['total_seconds'], 7 * 60)
        self.assertLess(data['total_seconds'], 8 * 60)
        self.assertNotEqual(data['total_seconds'], 30 * 60)

    def test_old_play_url_starts_session_without_minutes(self):
        self.client.login(username='player', password='pass12345')
        res = self.client.post(
            f'/plus/play/{self.game.id}/',
            {'minutes': '30'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload['playing'])
        pt = Playtime.objects.filter(user=self.user, game=self.game).first()
        self.assertTrue(pt is None or pt.seconds == 0)
