# articles/tasks.py
from collections import defaultdict
from celery import shared_task
from django.db import transaction
from .models import Article, PendingRating, Rating
import logging

# A batch counts as a burst when it has at least BURST_SIZE votes and its average is
# at least BURST_DROP below the article's current average. Only BURST_WEIGHT of a
# burst's deviation from the current average is applied.
BURST_SIZE = 100
BURST_DROP = 2.0
BURST_WEIGHT = 0.1


logger = logging.getLogger(__name__)


def is_burst(article, batch):
    if article.num_ratings == 0 or len(batch) < BURST_SIZE:
        return False
    batch_avg = sum(p.rating for p in batch) / len(batch)
    return article.avg_rating - batch_avg >= BURST_DROP


def apply_batch(article, batch):
    """
    Fold a batch of pending ratings into the article's running average.
    New votes add their rating, re-rates replace the user's previous rating.
    """
    weight = BURST_WEIGHT if is_burst(article, batch) else 1.0
    if weight < 1.0:
        logger.info(f"Dampening burst of {len(batch)} ratings on article {article.id}")

    current_sum = article.num_ratings * article.avg_rating
    delta = 0.0
    num_new_ratings = 0
    for pending in batch:
        effective = article.avg_rating + weight * (pending.rating - article.avg_rating)
        if pending.last_rate is None:
            num_new_ratings += 1
            delta += effective
        else:
            delta += effective - pending.last_rate

    article.num_ratings += num_new_ratings
    if article.num_ratings:
        article.avg_rating = round((current_sum + delta) / article.num_ratings, 2)
    article.save()


@shared_task
def process_pending_ratings():
    logger.debug("Starting to process pending ratings")

    with transaction.atomic():
        # Lock the rows we process so a rating submitted meanwhile isn't deleted unapplied.
        pending_ratings = list(PendingRating.objects.select_for_update())
        batches = defaultdict(list)
        for pending in pending_ratings:
            batches[pending.article_id].append(pending)

        for article_id, batch in batches.items():
            article = Article.objects.select_for_update().get(id=article_id)
            apply_batch(article, batch)
            logger.debug(f"Updated article {article.id}: num_ratings={article.num_ratings}, "
                         f"avg_rating={article.avg_rating}")

            for pending in batch:
                Rating.objects.update_or_create(
                    user_id=pending.user_id,
                    article=article,
                    defaults={'rating': pending.rating},
                )

        PendingRating.objects.filter(id__in=[p.id for p in pending_ratings]).delete()
        logger.debug(f"Processed and deleted {len(pending_ratings)} pending ratings")
