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
from .models import Article, Rating, PendingRating
from django.db.models import Count, Avg
from rest_framework.permissions import IsAuthenticated
from .tasks import process_pending_ratings




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
        
        articles = Article.objects.all()
        result = []
        
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
            result.append(article_data)


        return Response(result, status=status.HTTP_200_OK)


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
        
        existing_rating = Rating.objects.filter(user=user, article=article).first()    
            
        # Save the rating in PendingRating
        try:
            pending_rating, created = PendingRating.objects.update_or_create(
                user=user,
                article=article,
                defaults={'rating': rating_value,
                          'last_rate': existing_rating.rating if existing_rating else None,
                },
            )
        except Exception as e:
            pass
        # Trigger Celery task to process ratings in the background
        process_pending_ratings.apply_async(countdown=20)  # Delay the task by 60 seconds for batch processing

        return Response({"detail": "Rating submitted successfully and will be processed soon."},
                         status=status.HTTP_202_ACCEPTED)