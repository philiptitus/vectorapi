# Generated by Django 5.0.6 on 2024-07-14 09:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0012_alter_interviewcodingquestion_session_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interviewblock',
            name='session',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='iblocks', to='base.interviewsession'),
        ),
        migrations.AlterField(
            model_name='interviewsession',
            name='interview',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.interview'),
        ),
    ]
