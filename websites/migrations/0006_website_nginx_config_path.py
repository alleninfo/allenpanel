# Generated by Django 4.2.19 on 2025-02-09 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0005_website_path_website_user_alter_website_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='website',
            name='nginx_config_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
