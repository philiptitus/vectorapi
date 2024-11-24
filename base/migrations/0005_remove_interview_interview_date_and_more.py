# Generated by Django 5.0.6 on 2024-07-10 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_interview_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='interview',
            name='interview_date',
        ),
        migrations.RemoveField(
            model_name='preparationblock',
            name='content',
        ),
        migrations.AddField(
            model_name='interview',
            name='interview_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='preparationblock',
            name='score',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='preparationmaterial',
            name='score',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='job',
            name='mockup_interview_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='preparationblock',
            name='block_type',
            field=models.CharField(choices=[('QA', 'Question-Answer'), ('Code_Block', 'Code_Block'), ('YT', 'YouTube Video'), ('LINK', 'Link')], max_length=10),
        ),
    ]
