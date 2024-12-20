from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Article(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()

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
