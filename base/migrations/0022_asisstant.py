# Generated by Django 5.0.7 on 2024-08-21 10:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0021_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asisstant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.TextField()),
                ('question', models.TextField()),
                ('response', models.TextField()),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='asisstant', to='base.interviewsession')),
            ],
        ),
    ]
