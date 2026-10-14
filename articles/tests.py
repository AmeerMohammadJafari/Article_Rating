from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Article, PendingRating, Rating


class ArticleModelTests(TestCase):
    def test_add_rating_updates_running_average(self):
        article = Article.objects.create(title="t", content="c")

        article.add_rating(4)
        article.add_rating(2)

        article.refresh_from_db()
        self.assertEqual(article.num_ratings, 2)
        self.assertAlmostEqual(article.avg_rating, 3.0)


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_creates_user(self):
        response = self.client.post("/api/signup/", {"username": "ali", "password": "pw12345"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="ali").exists())

    def test_signup_rejects_duplicate_username(self):
        User.objects.create_user(username="ali", password="pw12345")

        response = self.client.post("/api/signup/", {"username": "ali", "password": "other"}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_login_returns_token(self):
        user = User.objects.create_user(username="ali", password="pw12345")

        response = self.client.post("/api/login/", {"username": "ali", "password": "pw12345"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token"], Token.objects.get(user=user).key)

    def test_login_rejects_wrong_password(self):
        User.objects.create_user(username="ali", password="pw12345")

        response = self.client.post("/api/login/", {"username": "ali", "password": "wrong"}, format="json")

        self.assertEqual(response.status_code, 401)


class AuthenticatedAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="pw12345")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.article = Article.objects.create(title="Go vs Python", content="...")


class ArticleListTests(AuthenticatedAPITestCase):
    def test_requires_authentication(self):
        response = APIClient().get("/api/articles/")

        self.assertEqual(response.status_code, 401)

    def test_includes_the_users_own_rating(self):
        Rating.objects.create(article=self.article, user=self.user, rating=4)

        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["user_rating"], 4)

    def test_user_rating_is_none_when_not_rated(self):
        response = self.client.get("/api/articles/")

        self.assertIsNone(response.data[0]["user_rating"])


@patch("articles.views.process_pending_ratings.apply_async")
class SubmitRatingTests(AuthenticatedAPITestCase):
    def url(self, article_id=None):
        return f"/articles/{article_id or self.article.id}/rate/"

    def test_queues_rating_and_schedules_processing(self, apply_async):
        response = self.client.post(self.url(), {"rating": 5}, format="json")

        self.assertEqual(response.status_code, 202)
        pending = PendingRating.objects.get(article=self.article, user=self.user)
        self.assertEqual(pending.rating, 5)
        self.assertIsNone(pending.last_rate)
        apply_async.assert_called_once()

    def test_records_previous_rating_when_user_re_rates(self, apply_async):
        Rating.objects.create(article=self.article, user=self.user, rating=2)

        self.client.post(self.url(), {"rating": 5}, format="json")

        self.assertEqual(PendingRating.objects.get(user=self.user).last_rate, 2)

    def test_resubmitting_keeps_one_pending_rating(self, apply_async):
        self.client.post(self.url(), {"rating": 1}, format="json")
        self.client.post(self.url(), {"rating": 3}, format="json")

        self.assertEqual(PendingRating.objects.filter(user=self.user).count(), 1)
        self.assertEqual(PendingRating.objects.get(user=self.user).rating, 3)

    def test_rejects_invalid_ratings(self, apply_async):
        for value in (-1, 6, "4", None, True):
            with self.subTest(value=value):
                response = self.client.post(self.url(), {"rating": value}, format="json")

                self.assertEqual(response.status_code, 400)
        self.assertFalse(PendingRating.objects.exists())
        apply_async.assert_not_called()

    def test_unknown_article_returns_404(self, apply_async):
        response = self.client.post(self.url(article_id=9999), {"rating": 3}, format="json")

        self.assertEqual(response.status_code, 404)
