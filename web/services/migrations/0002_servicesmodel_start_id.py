# Generated by Django 3.2.12 on 2022-04-08 14:49
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicesmodel",
            name="start_id",
            field=models.TextField(default="abcdefgh", verbose_name="start_id"),
            preserve_default=False,
        ),
    ]
