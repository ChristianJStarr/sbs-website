# Generated by Django 3.1.6 on 2021-12-09 02:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broadcasts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='clip',
            name='thumbnail_image',
            field=models.ImageField(default='broadcast-thumbnails/clips/default.jpg', upload_to='broadcast-thumbnails/clips/'),
        ),
        migrations.AddField(
            model_name='fullvod',
            name='thumbnail_image',
            field=models.ImageField(default='broadcast-thumbnails/vods/default.jpg', upload_to='broadcast-thumbnails/vods/'),
        ),
        migrations.AddField(
            model_name='stream',
            name='thumbnail_image',
            field=models.ImageField(default='broadcast-thumbnails/streams/default.jpg', upload_to='broadcast-thumbnails/streams/'),
        ),
    ]
