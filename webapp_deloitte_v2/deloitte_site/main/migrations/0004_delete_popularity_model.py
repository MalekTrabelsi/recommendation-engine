# Generated by Django 3.2 on 2021-04-14 00:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_remove_popularity_model_model_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='popularity_model',
        ),
    ]
