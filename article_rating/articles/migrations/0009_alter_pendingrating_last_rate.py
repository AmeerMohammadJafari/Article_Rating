# Generated by Django 5.1.4 on 2024-12-20 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0008_alter_pendingrating_last_rate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pendingrating',
            name='last_rate',
            field=models.IntegerField(default=0, null=True),
        ),
    ]
