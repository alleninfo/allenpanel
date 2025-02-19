# Generated by Django 4.2.19 on 2025-02-09 14:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0003_alter_website_php_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='website',
            name='port',
            field=models.IntegerField(default=80),
        ),
        migrations.AlterField(
            model_name='website',
            name='php_version',
            field=models.CharField(choices=[('none', '不使用'), ('7.4', 'PHP 7.4'), ('8.0', 'PHP 8.0'), ('8.1', 'PHP 8.1'), ('8.2', 'PHP 8.2')], default='none', max_length=10, verbose_name='PHP版本'),
        ),
    ]
