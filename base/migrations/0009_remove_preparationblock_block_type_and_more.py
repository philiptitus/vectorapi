# Generated by Django 5.0.6 on 2024-07-12 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_codingquestion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preparationblock',
            name='block_type',
        ),
        migrations.RemoveField(
            model_name='preparationblock',
            name='resource_link',
        ),
        migrations.AddField(
            model_name='codingquestion',
            name='score',
            field=models.FloatField(default=0),
        ),
    ]
