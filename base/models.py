from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission
from django.conf import settings
# Create your models here.
from django.utils import timezone



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)




AUTH_PROVIDERS = {'email': 'email', 'google': 'google', 'github': 'github', 'linkedin': 'linkedin'}

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    avi = models.ImageField(null=True, blank=True, default='/avatar.png')
    isPrivate = models.BooleanField(default=False)
    auth_provider = models.CharField(max_length=50, blank=False, null=False, default=AUTH_PROVIDERS.get('email'))
    
    # Adding the credits field with a default value of 1000
    credits = models.IntegerField(default=1000)

    # Adding the requested integer fields with default values of 0
    tjobs = models.IntegerField(default=0)
    usessions = models.IntegerField(default=0)
    csessions = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)


    google_calendar_token = models.CharField(max_length=255, null=True, blank=True)
    google_calendar_refresh_token = models.CharField(max_length=255, null=True, blank=True)
    google_calendar_token_expiry = models.DateTimeField(null=True, blank=True)

    google_token = models.CharField(max_length=255, null=True, blank=True)
    google_refresh_token = models.CharField(max_length=255, null=True, blank=True)
    allow_Calendar = models.BooleanField(default=False)

    objects = CustomUserManager()
    user_permissions = models.ManyToManyField(Permission, verbose_name='user permissions', blank=True)

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.email
    
    def tokens(self):    
        refresh = RefreshToken.for_user(self)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }




class Job(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    actual_interview_date = models.DateField()
    mockup_interview_date = models.DateField(blank=True, null=True)
    job_url = models.URLField(blank=True, null=True)  # Optional URL field

    def __str__(self):
        return self.title







class Interview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    interview_datetime = models.DateTimeField(blank=True, null=True)
    passed = models.BooleanField(default=False)


    def __str__(self):
        return f"Interview for {self.job.title} on {self.interview_datetime}"




class PreparationMaterial(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # Set default to the current time

    def __str__(self):
        return self.title
    

class PreparationBlock(models.Model):

    preparation_material = models.ForeignKey(PreparationMaterial, on_delete=models.CASCADE, related_name='blocks')
    question = models.TextField(blank=True, null=True)
    answer = models.TextField(blank=True, null=True)
    my_answer = models.TextField(blank=True, null=True)
    attempted = models.BooleanField(default=False)

    score = models.FloatField(default=0)  # New field for the score of each block

    # def __str__(self):
    #     return f"{self.id()} Block for {self.preparation_material.title}"


class GoogleSearchResult(models.Model):
    preparation_material = models.ForeignKey(PreparationMaterial, on_delete=models.CASCADE, related_name='blocks_2')
    title = models.CharField(max_length=255)
    snippet = models.TextField()
    link = models.URLField()
    attempted = models.BooleanField(default=False)


    def __str__(self):
        return self.title
    


class CodingQuestion(models.Model):
    preparation_material = models.ForeignKey(PreparationMaterial, on_delete=models.CASCADE, related_name='coding_questions')
    question = models.TextField()
    answer = models.TextField()
    my_answer = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=100)
    score = models.FloatField(default=0)  # New field for the score of each block
    attempted = models.BooleanField(default=False)


    def __str__(self):
        return self.question








class YouTubeLink(models.Model):
    preparation_material = models.ForeignKey(PreparationMaterial, on_delete=models.CASCADE, related_name='blocks_3')
    title = models.CharField(max_length=255)
    embed_url = models.URLField()
    attempted = models.BooleanField(default=False)


    def __str__(self):
        return self.title













class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} at {self.timestamp}"




from django.utils import timezone
from datetime import timedelta

class InterviewSession(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    score = models.FloatField(default=0)  # New field for the overall score
    expired = models.BooleanField(default=False)
    marked = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)




 

    def __str__(self):
        return f"Session for {self.interview.job.title} starting at {self.start_time}"


class Asisstant(models.Model):
    session = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='asisstant')
    query = models.TextField()
    question = models.TextField()
    response = models.TextField()
    last_interaction = models.DateTimeField(blank=True, null=True)
    ready = models.BooleanField(default=False)


    def __str__(self):
        return f"Assistant response for session {self.session.id}"


class Code(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    script = models.TextField()
    response = models.TextField()
    ready = models.BooleanField(default=False)


    def __str__(self):
        return f"Code submission by {self.user.username}"

class InterviewBlock(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='iblocks')
    question = models.TextField(blank=True, null=True)
    answer = models.TextField(blank=True, null=True)
    my_answer = models.TextField(blank=True, null=True)
    score = models.FloatField(default=0)  # New field for the score of each block


    time_taken = models.DurationField(blank=True, null=True)

    def __str__(self):
        return f"Block for session {self.session.id}: {self.question[:30]}"




class InterviewCodingQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE , related_name='icoding_questions')
    question = models.TextField()
    answer = models.TextField()
    my_answer = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=100)
    score = models.FloatField(default=0)  # New field for the score of each block
    attempted = models.BooleanField(default=False)


    def __str__(self):
        return self.question





class Agent(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE)
    query = models.TextField()
    question = models.TextField()
    response = models.TextField()

    def __str__(self):
        return f"Agent: {self.query[:50]}..."  # Display the first 50 characters of the query

