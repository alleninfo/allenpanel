# Generated by Django 4.2.19 on 2025-02-10 00:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='website',
            name='path',
        ),
        migrations.AlterField(
            model_name='website',
            name='php_version',
            field=models.CharField(choices=[('none', '不使用')], default='none', max_length=10, verbose_name='PHP版本'),
        ),
    ]
