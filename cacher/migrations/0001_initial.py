# Generated by Django 3.1.6 on 2021-09-25 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Homepage_Cache',
            fields=[
                ('cache_id', models.IntegerField(default=0, primary_key=True, serialize=False)),
                ('tournament_winners', models.BinaryField(blank=True, null=True)),
                ('top_ten_rankings', models.BinaryField(blank=True, null=True)),
                ('recent_tournament', models.BinaryField(blank=True, null=True)),
                ('bowler_of_month', models.BinaryField(blank=True, null=True)),
            ],
        ),
    ]
