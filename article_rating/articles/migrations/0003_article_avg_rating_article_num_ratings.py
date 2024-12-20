# Generated by Django 5.1.4 on 2024-12-20 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0002_rating_created_at_alter_rating_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='avg_rating',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='article',
            name='num_ratings',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
