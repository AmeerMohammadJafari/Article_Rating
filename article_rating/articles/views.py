from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token
from .models import Article, Rating
from django.db.models import Count, Avg
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta



class LoginView(APIView):
    permission_classes = [AllowAny]  # Allow unauthenticated users to access

    def post(self, request):
        # Get username and password from request body
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"detail": "Username and password are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid credentials. Please try again.")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationFailed("User is inactive.")

        # Generate token for the authenticated user
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "message": "Login successful.",
            "token": token.key
        }, status=status.HTTP_200_OK)




class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            raise ValidationError("Username and password are required.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")


        # Create and save the user
        user = User.objects.create_user(username=username, password=password)
        return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)




class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Check if the cached data exists
        # cached_data = cache.get('article_list')
        # if cached_data:
        #     return Response(cached_data, status=status.HTTP_200_OK)

        articles = Article.objects.annotate(
            num_ratings=Count('ratings'),
            avg_rating=Avg('ratings__rating')
        )

        article_list = []

        for article in articles:
            user_rating = Rating.objects.filter(article=article, user=request.user).first()
            user_rating_value = user_rating.rating if user_rating else None

            article_data = {
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'num_ratings': article.num_ratings,
                'avg_rating': article.avg_rating if article.avg_rating is not None else 0,
                'user_rating': user_rating_value
            }

            article_list.append(article_data)

        # Cache the result for 5 minutes
        # cache.set('article_list', article_list, timeout=300)

        return Response(article_list, status=status.HTTP_200_OK)


class SubmitRatingView(APIView):
    permission_classes = [IsAuthenticated]
    

    def post(self, request, article_id):
        # Get the rating from the request body
        rating_value = request.data.get('rating')

        # Validate the rating
        if rating_value is None or not (0 <= rating_value <= 5):
            return Response({"detail": "Rating must be between 0 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the article
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response({"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # Check if the user has already rated this article
        existing_rating = Rating.objects.filter(user=user, article=article).first()

        if existing_rating:
            # Update the existing rating if the user has already rated the article
            existing_rating.rating = rating_value
            existing_rating.save()
        else:
            # Create a new rating if the user hasn't rated this article
            Rating.objects.create(user=user, article=article, rating=rating_value)

        # Calculate the weighted average rating of the article
        weighted_avg = self.calculate_weighted_average(article)

        # Return a success response
        return Response({
            "detail": "Rating submitted successfully",
            "weighted_avg": weighted_avg
        }, status=status.HTTP_200_OK)

    def calculate_weighted_average(self, article):
        """
        Calculate the weighted average based on the ratings in the last 24 hours.
        More recent ratings are weighted higher to reduce the effect of sudden fluctuations.
        """
        # Get the ratings from the last 24 hours (rolling average)
        recent_ratings = Rating.objects.filter(
            article=article,
            created_at__gte=timezone.now() - timedelta(days=1)
        )

        total_ratings = recent_ratings.count()
        if total_ratings == 0:
            return 0  # No ratings in the last 24 hours

        # Calculate the weighted sum of ratings, applying weight decay over time
        weighted_sum = 0
        weight_decay_factor = 0.9  # Decay factor for how much recent ratings should weigh

        for rating in recent_ratings:
            # Apply the decay function (more recent ratings have higher weight)
            time_diff = timezone.now() - rating.created_at
            weight = weight_decay_factor ** (time_diff.total_seconds() / 3600)  # Decay over hours
            weighted_sum += rating.rating * weight

        # Return the weighted average rounded to 2 decimal places
        weighted_avg = weighted_sum / total_ratings
        return round(weighted_avg, 2)
        