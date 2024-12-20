# articles/tasks.py
from celery import shared_task
from django.db import transaction
from django.utils.timezone import now
from datetime import timedelta
from .models import Article, PendingRating, Rating
from django.db.models import Avg, Count, Q
import logging
from django.db.models.functions import Coalesce


logger = logging.getLogger(__name__)

@shared_task
def process_pending_ratings():
    logger.debug("Starting to process pending ratings")
    pending_ratings = PendingRating.objects.values('article').annotate(
    avg_current_rating=Avg('rating'),
    avg_last_rating=Avg(Coalesce('last_rate', 0)),  # Replace NULL values with 0 for average calculation
    num_all_pending_ratings=Count('rating'),
    num_new_ratings=Count('rating', filter=Q(last_rate=None))  # Count only where last_rate = None
    )

    logger.debug(f"Found pending ratings: {pending_ratings}")

    with transaction.atomic():
        for entry in pending_ratings:
            article = Article.objects.select_for_update().get(id=entry['article'])
            avg_current_rating = entry['avg_current_rating']
            avg_last_rating = entry['avg_last_rating']
            num_new_ratings = entry['num_new_ratings']
            num_all_pending_ratings = entry['num_all_pending_ratings']

            logger.debug(f"Processing article {article.id}: avg_current_rating={avg_current_rating}, "
                            f"avg_last_rating={avg_last_rating}, new_num_ratings={num_new_ratings}")

            current_sum = article.num_ratings * article.avg_rating
            new_sum = current_sum + (num_all_pending_ratings * (avg_current_rating - avg_last_rating))
            article.num_ratings += num_new_ratings
            article.avg_rating = round(new_sum / article.num_ratings, 2)
            article.save()

            logger.debug(f"Updated article {article.id}: num_ratings={article.num_ratings}, "
                            f"avg_rating={article.avg_rating}")

            pending_ratings_for_article = PendingRating.objects.filter(article=article)
            for pending_rating in pending_ratings_for_article:
                Rating.objects.update_or_create(
                    user=pending_rating.user,
                    article=article,
                    defaults={'rating': pending_rating.rating},
                )
        PendingRating.objects.all().delete()
        logger.debug("Processed and deleted pending ratings")
   