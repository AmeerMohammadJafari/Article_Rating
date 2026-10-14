from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Article(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    num_ratings = models.PositiveIntegerField(default=0)
    avg_rating = models.FloatField(default=0)
    
    
    
    def add_rating(self, new_rating):
        """
        Update num_ratings and avg_rating after adding a new rating.
        """
        # Calculate current total sum of ratings
        current_sum = self.num_ratings * self.avg_rating

        # Update num_ratings
        self.num_ratings += 1

        # Calculate new average
        self.avg_rating = (current_sum + new_rating) / self.num_ratings

        # Save changes to the database
        self.save()
        
        

    def __str__(self):
        return self.title


class Rating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(6)])  # Rating between 0 and 5
    created_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = ['article', 'user']  # Ensure one rating per user per article

    def __str__(self):
        return f"Rating {self.rating} by {self.user.username} for {self.article.title}"


class PendingRating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="pending_ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(6)])  # Rating between 0 and 5
    created_at = models.DateTimeField(auto_now=True)
    last_rate = models.IntegerField(null=True, default=0)  # Last rating by the user for the article
    
    
    class Meta:
        unique_together = ['article', 'user']  # Ensure one pending rating per user per article
