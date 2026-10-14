from django.contrib import admin

from .models import Article, PendingRating, Rating

admin.site.register(Article)
admin.site.register(Rating)
admin.site.register(PendingRating)
