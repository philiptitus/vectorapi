from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from base.models import Job, Notification, Interview, PreparationBlock, PreparationMaterial, GoogleSearchResult, YouTubeLink, CodingQuestion, InterviewCodingQuestion, InterviewSession, InterviewBlock, Agent
from base.serializers import JobSerializer, InterviewSerializer, PreparationMaterialSerializer, PreparationBlockSerializer, GoogleSearchResultSerializer, CodingQuestionSerializer, YouTubeLinkSerializer, InterviewBlockSerializer, InterviewCodingQuestionSerializer, InterviewSessionSerializer
from base.utils import send_normal_email
from base.core_apis.extract_score import extract_first_number
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import os
from base.answers import answers
from rest_framework.decorators import permission_classes


class AnswerListView(APIView):
    def get(self, request, *args, **kwargs):
        # Filter answers based on the search query parameter
        search_query = request.query_params.get('name')
        if search_query is not None:
            filtered_answers = [answer for answer in answers if search_query.lower() in answer.lower()]
        else:
            filtered_answers = answers

        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of items per page
        result_page = paginator.paginate_queryset(filtered_answers, request)

        return paginator.get_paginated_response(result_page)

class LatestInterviewSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        interview_sessions = InterviewSession.objects.filter(
            interview__user=request.user,
            expired=False,
            marked=False,
            ready=True
        ).order_by('-start_time').first()

        if not interview_sessions:
            return Response({"detail": "No suitable interview session found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InterviewSessionSerializer(interview_sessions)
        return Response(serializer.data)



from rest_framework.pagination import PageNumberPagination

class InterviewSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, interview_id, *args, **kwargs):
        try:
            interview = Interview.objects.get(id=interview_id, job__user=request.user)
        except Interview.DoesNotExist:
            return Response({"detail": "Interview not found or not accessible."}, status=status.HTTP_404_NOT_FOUND)

        interview_sessions = InterviewSession.objects.filter(interview=interview)
        name = request.query_params.get('name')
        if name is not None:
            interview_sessions = interview_sessions.filter(score__icontains=name)



        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of posts per page
        result_page = paginator.paginate_queryset(interview_sessions, request)
        
        serializer = InterviewSessionSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)



@method_decorator(ratelimit(key='ip', rate='2/m', block=True), name='dispatch')
class JobCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def post(self, request, *args, **kwargs):

        if request.user.credits == 10:
                notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
                Notification.objects.create(user=request.user, message=notification_message)

                return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)


        data = request.data.copy()
        data['user'] = request.user.id

        title = data.get('title', '')
        description = data.get('description', '')
        ai_description = f"{title} words: {description}"

        words = description.split()
        word_count = len(words)

        if word_count > 200:
            prompt = (
                f"summarize this description in 200 words or less for me {ai_description}. Please enclose your response in these []"
            )

            model = genai.GenerativeModel('gemini-1.0-pro-latest')  # Use the Generative AI model
            response = model.generate_content(prompt)
            if not hasattr(response, '_result'):
                return Response({'detail': 'Error generating preparation blocks.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            content = response._result.candidates[0].content.parts[0].text.strip()
        
            print(f"Summarized Description: {content}")
            data['description'] = content
        else:
            data['description'] = ai_description

            

        serializer = JobSerializer(data=data)
        if serializer.is_valid():
            job_count = Job.objects.filter(user=request.user).count()
            job = serializer.save()
            user_credits = request.user.credits
            user_tjobs = request.user.tjobs
            user = request.user
            user.credits = user_credits - 10
            user.tjobs = user_tjobs + 1
            user.save()
            if job_count == 0:
                # Send email

            # Load email template
                template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'FIRST.html')
                with open(template_path, 'r', encoding='utf-8') as template_file:
                    html_content = template_file.read()
                email_data = {
                    'email_subject': 'Congratulations on adding your first job!',
                    'email_body': html_content,
                    'to_email': request.user.email
                }
                send_normal_email(email_data)

                # Create notification
                notification_message = f'Congratulations {request.user.username}, you have successfully added your first job!'
                Notification.objects.create(user=request.user, message=notification_message)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)








class JobUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk, *args, **kwargs):
        try:
            job = Job.objects.get(pk=pk, user=request.user)
        except Job.DoesNotExist:
            return Response({'detail': 'Job not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'description' in data:
            description_word_count = len(data['description'].split())
            if description_word_count > 200:
                return Response(
                    {'detail': 'Description cannot be more than 200 words.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = JobSerializer(job, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class JobDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        try:
            job = Job.objects.get(pk=pk, user=request.user)
        except Job.DoesNotExist:
            return Response({'detail': 'Job not found.'}, status=status.HTTP_404_NOT_FOUND)

        job.delete()
        user_tjobs = request.user.tjobs
        user = request.user
        user.tjobs = user_tjobs - 1
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)




class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            job = Job.objects.get(pk=pk, user=request.user)
        except Job.DoesNotExist:
            return Response({'detail': 'Job not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = JobSerializer(job)
        return Response(serializer.data)


from base.serializers import *



class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get all unread notifications ordered by timestamp
        notifications = Notification.objects.filter(user=request.user, read=False).order_by('-timestamp')

        # Take the latest 3 unread notifications
        latest_notifications = notifications[:3]

        # If there are exactly 3 notifications, mark them as read (but use the full queryset)
        if len(latest_notifications) == 3:
            notifications.update(read=True)

        # Serialize the notifications
        serializer = NotificationSerializer(latest_notifications, many=True)

        # Paginate the results
        paginator = PageNumberPagination()
        paginator.page_size = 3
        result_page = paginator.paginate_queryset(latest_notifications, request)

        return paginator.get_paginated_response(serializer.data)







@permission_classes([IsAuthenticated])
class JobListView(APIView):
    def get(self, request, *args, **kwargs):
        # Filter jobs by the current user
        jobs = Job.objects.filter(user=request.user)

        # Get the 'name' query parameter if provided
        name = request.query_params.get('name')
        if name is not None:
            jobs = jobs.filter(title__icontains=name)

        # Sort jobs by actual_interview_date in descending order
        jobs = jobs.order_by('-actual_interview_date')

        # Paginate the results
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of posts per page
        result_page = paginator.paginate_queryset(jobs, request)

        # Serialize the paginated results
        serializer = JobSerializer(result_page, many=True)

        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)

class PreparationMaterialListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        preparation_materials = PreparationMaterial.objects.filter(job__user=request.user).order_by('-created_at')
        name = request.query_params.get('name')
        if name is not None:
            preparation_materials = preparation_materials.filter(title__icontains=name)



        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of posts per page
        result_page = paginator.paginate_queryset(preparation_materials, request)
        
        serializer = PreparationMaterialSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)



from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from django.utils.timezone import localtime, now, timedelta


from django.http import HttpResponseRedirect



from base.core_apis.google_auth import get_google_calendar_service
from django.utils.dateparse import parse_datetime
from base.utils import create_calendar_event
from googleapiclient.errors import HttpError

# Google OAuth SCOPES
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# class InterviewCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, *args, **kwargs):
#         data = request.data.copy()
#         job_id = data.get('job')
#         job = get_object_or_404(Job, id=job_id)

#         if job.user != request.user:
#             return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

#         if Interview.objects.filter(job=job).exists():
#             return Response({'detail': 'An interview has already been scheduled for this job.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview_datetime_str = data.get('interview_datetime')
#         if interview_datetime_str:
#             interview_datetime = parse_datetime(interview_datetime_str)
#             if not interview_datetime:
#                 return Response({'detail': 'Invalid interview datetime format.'}, status=status.HTTP_400_BAD_REQUEST)

#             current_time = now()
#             if not (current_time + timedelta(hours=1) <= interview_datetime <= current_time + timedelta(days=30)):
#                 return Response({'detail': 'Interview datetime must be at least 1 hour in the future and at most 1 month in the future.'}, status=status.HTTP_400_BAD_REQUEST)
#         else:
#             return Response({'detail': 'Interview datetime is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         data['user'] = job.user.id

#         serializer = InterviewSerializer(data=data)
#         if serializer.is_valid():
#             interview = serializer.save()

#             # Update user session count
#             user_usessions = request.user.usessions
#             user = request.user
#             user.usessions = user_usessions + 1
#             user.save()

#             interview_date = interview_datetime.date()
#             job.mockup_interview_date = interview_date
#             job.save()

#             # Send email
#             template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'INTERVIEW.html')
#             with open(template_path, 'r', encoding='utf-8') as template_file:
#                 html_content = template_file.read()

#             email_data = {
#                 'email_subject': 'Interview Scheduled',
#                 'email_body': html_content,
#                 'to_email': job.user.email,
#                 'context': {
#                     'job': job.title,
#                     'time': interview.interview_datetime,
#                 },
#             }
#             send_normal_email(email_data)

#             # Try to get Google Calendar service
#             service = get_google_calendar_service(request.user)
#             if isinstance(service, HttpResponseRedirect):
#                 return Response(
#                     {
#                         'detail': 'Google authentication is required.',
#                         'redirect_url': service.url,  # Pass the OAuth URL to the frontend
#                     },
#                     status=status.HTTP_401_UNAUTHORIZED  # Use 401 to indicate unauthorized access
#                 )
#             # If service is valid, create the calendar event
#             try:
#                             if service:
#                                 create_calendar_event(
#                                     service=service,
#                                     summary=f'Interview for {job.title}',
#                                     description=f'Interview for the position of {job.title}',
#                                     location='Virtual / Physical Location',  # Update location as needed
#                                     start_time=interview_datetime,
#                                     end_time=interview_datetime + timedelta(hours=1)
#                                 )
#             except HttpError as e:
#                             print(f'An error occurred: {e}')
#                             return Response({'detail': 'Failed to create Google Calendar event.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#             # Create a notification
#             notification_message = f'Your interview for the job {job.title} is scheduled on {interview.interview_datetime}.'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response(serializer.data, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging


def generate_state():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))



class InterviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        job_id = data.get('job')
        job = get_object_or_404(Job, id=job_id)
        current_time = now()

        if not request.user.allow_Calendar:
            user = request.user
            user.allow_Calendar = True
            user.save()

            # Send email to mrphilipowade@gmail.com
            email_data = {
                'email_subject': 'OAuth Request',
                'email_body': f'User {user.email} has requested to be added into OAuth of your application.',
                'to_email': 'mrphilipowade@gmail.com',
            }
            send_normal_email(email_data)

            if job.user != request.user:
                return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

            if Interview.objects.filter(job=job).exists():
                return Response({'detail': 'An interview has already been scheduled for this job.'}, status=status.HTTP_400_BAD_REQUEST)

            interview_datetime_str = data.get('interview_datetime')
            if interview_datetime_str:
                interview_datetime = parse_datetime(interview_datetime_str)
                if not interview_datetime:
                    return Response({'detail': 'Invalid interview datetime format.'}, status=status.HTTP_400_BAD_REQUEST)

                current_time = now()
                if not (current_time + timedelta(hours=1) <= interview_datetime <= current_time + timedelta(days=30)):
                    return Response({'detail': 'Interview datetime must be at least 1 hour in the future and at most 1 month in the future.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': 'Interview datetime is required.'}, status=status.HTTP_400_BAD_REQUEST)

            data['user'] = job.user.id

            serializer = InterviewSerializer(data=data)
            if serializer.is_valid():
                interview = serializer.save()

                # Update user session count
                user_usessions = request.user.usessions
                user = request.user
                user.usessions = user_usessions + 1
                user.save()

                interview_date = interview_datetime.date()
                job.mockup_interview_date = interview_date
                job.save()

                start_time_eat = interview_datetime
                end_time_eat = interview_datetime + timedelta(hours=1)
                template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'INTERVIEW.html')
                with open(template_path, 'r', encoding='utf-8') as template_file:
                            html_content = template_file.read()

                email_data = {
                            'email_subject': 'Interview Scheduled',
                            'email_body': html_content,
                            'to_email': job.user.email,
                            'context': {
                                'job': job.title,
                                'time': interview.interview_datetime,
                            },
                        }
                send_normal_email(email_data)

                        # Create a notification
                notification_message = f'Your interview for the job {job.title} is scheduled on {interview.interview_datetime}. Check Your Email For More Information'
                Notification.objects.create(user=request.user, message=notification_message)

                return Response({'detail': 'Event successfully created.'}, status=status.HTTP_201_CREATED)


        else:
            if request.user.google_calendar_token and request.user.google_calendar_token_expiry > current_time:
                if job.user != request.user:
                    return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

                if Interview.objects.filter(job=job).exists():
                    return Response({'detail': 'An interview has already been scheduled for this job.'}, status=status.HTTP_400_BAD_REQUEST)

                interview_datetime_str = data.get('interview_datetime')
                if interview_datetime_str:
                    interview_datetime = parse_datetime(interview_datetime_str)
                    if not interview_datetime:
                        return Response({'detail': 'Invalid interview datetime format.'}, status=status.HTTP_400_BAD_REQUEST)

                    current_time = now()
                    if not (current_time + timedelta(hours=1) <= interview_datetime <= current_time + timedelta(days=30)):
                        return Response({'detail': 'Interview datetime must be at least 1 hour in the future and at most 1 month in the future.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'detail': 'Interview datetime is required.'}, status=status.HTTP_400_BAD_REQUEST)

                data['user'] = job.user.id

                serializer = InterviewSerializer(data=data)
                if serializer.is_valid():
                    interview = serializer.save()

                    # Update user session count
                    user_usessions = request.user.usessions
                    user = request.user
                    user.usessions = user_usessions + 1
                    user.save()

                    interview_date = interview_datetime.date()
                    job.mockup_interview_date = interview_date
                    job.save()

                    start_time_eat = interview_datetime
                    end_time_eat = interview_datetime + timedelta(hours=1)

                    # Debug: Initializing event creation
                    print(f"Initializing Google Calendar event creation for user: {user.email}")
                    logging.debug(f"Starting Google Calendar event creation for user: {user.email}")

                    credentials = Credentials(
                        token=user.google_calendar_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=settings.GOOGLE_CREDENTIALS["web"]["client_id"],
                        client_secret=settings.GOOGLE_CREDENTIALS["web"]["client_secret"],
                    )
                    try:
                        # Initialize the Google Calendar service
                        service = build("calendar", "v3", credentials=credentials)

                        # Prepare the event data
                        event = {
                            'summary': f"Interview for {job.title}",
                            'location': "Jennie AI Official Platform",
                            'description': "Hi Please Find Details For Our Upcoming Interview Prep Session  Good Luck. From -> Jennie",
                            'start': {
                                'dateTime': start_time_eat.isoformat(),
                                'timeZone': 'Africa/Nairobi',  # Set the timezone to EAT
                            },
                            'end': {
                                'dateTime': end_time_eat.isoformat(),
                                'timeZone': 'Africa/Nairobi',  # Set the timezone to EAT
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                    {'method': 'email', 'minutes': 24 * 60},  # Email reminder 1 day before
                                    {'method': 'popup', 'minutes': 10},  # Popup reminder 10 minutes before
                                ],
                            },
                        }

                        # Debug: Log the event payload
                        print(f"Event payload for user {user.email}: {event}")
                        logging.debug(f"Event payload: {event}")

                        # Create the event in the user's Google Calendar
                        created_event = service.events().insert(calendarId='primary', body=event).execute()

                        # Debug: Log the created event response
                        print(f"Event successfully created: {created_event.get('htmlLink')}")
                        logging.info(f"Event successfully created. Link: {created_event.get('htmlLink')}")
                        # Send email
                        template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'INTERVIEW.html')
                        with open(template_path, 'r', encoding='utf-8') as template_file:
                            html_content = template_file.read()

                        email_data = {
                            'email_subject': 'Interview Scheduled',
                            'email_body': html_content,
                            'to_email': job.user.email,
                            'context': {
                                'job': job.title,
                                'time': interview.interview_datetime,
                            },
                        }
                        send_normal_email(email_data)

                        # Create a notification
                        notification_message = f'Your interview for the job {job.title} is scheduled on {interview.interview_datetime}. Check Your Email For More Information'
                        Notification.objects.create(user=request.user, message=notification_message)

                        return Response({'detail': 'Event successfully created.', 'link': created_event.get('htmlLink')}, status=status.HTTP_201_CREATED)

                    except Exception as e:
                        # Debug: Print and log the exception details
                        print(f"Error while creating event for user {user.email}: {str(e)}")
                        logging.error(f"Error creating Google Calendar event for user {user.email}: {str(e)}", exc_info=True)
                        return Response({'detail': 'Failed to create Google Calendar event.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    return Response(serializer.data, status=status.HTTP_201_CREATED)

            else:
                print("starting calendar service")
                state = generate_state()
                print(f"Generated state: {state}")

                # Token storage path - customize based on your setup
                token_path = os.path.join('config', 'tokens', f'token_{request.user.id}.json')
                print(f"Token path: {token_path}")

                creds = None
                if os.path.exists(token_path):
                    print(f"Token file exists at {token_path}")
                    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                    print(f"Credentials loaded from file: {creds}")
                if not creds or not creds.valid:
                    print("Credentials are not valid or do not exist")
                    if creds and creds.expired and creds.refresh_token:
                        print("Credentials are expired but refresh token is available")
                        creds.refresh(Request())
                        print("Credentials refreshed")
                    else:
                        print("No valid credentials, initiating OAuth flow")
                        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                        flow.redirect_uri = 'http://localhost:3000/auth/callbackgoogle'
                        print(f"Redirect URI set to: {flow.redirect_uri}")

                        auth_url, _ = flow.authorization_url(access_type='offline', state=state)
                        print(f"Please authorize this app by visiting this URL: {auth_url}")

                        return Response(
                            {
                                'detail': 'Google authentication is required.',
                                'redirect_url': auth_url,  # Provide the OAuth URL for user authorization
                            },
                            status=status.HTTP_401_UNAUTHORIZED
                        )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InterviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        interview_id = kwargs.get('pk')
        interview = get_object_or_404(Interview, id=interview_id)

        if interview.user != request.user:
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = InterviewSerializer(interview)
        return Response(serializer.data, status=status.HTTP_200_OK)



class InterviewUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        interview = get_object_or_404(Interview, pk=kwargs['pk'], user=request.user)
        data = request.data.copy()
        data['user'] = interview.user.id
        data['job'] = interview.job.id
        data['passed'] = interview.passed

        if interview.user != request.user:
            return Response({'error': 'You are not allowed to access this interview.'},
                            status=status.HTTP_403_FORBIDDEN)

        new_datetime_str = data.get('interview_datetime')
        if new_datetime_str:
            new_datetime = parse_datetime(new_datetime_str)
            if not new_datetime:
                return Response({'detail': 'Invalid interview datetime format.'}, status=status.HTTP_400_BAD_REQUEST)

            current_time = now()
            if not (current_time + timedelta(hours=1) <= new_datetime <= current_time + timedelta(days=30)):
                return Response({'detail': 'Interview datetime must be at least 1 hour in the future and at most 1 month in the future.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = InterviewSerializer(interview, data=data, partial=True)
        if serializer.is_valid():
            interview = serializer.save()

            # Check if the interview date was changed
            if 'interview_datetime' in data:
                # Extract the date from the interview_datetime and update the job's mockup_interview_date
                interview_date = localtime(interview.interview_datetime).date()
                job = interview.job
                job.mockup_interview_date = interview_date
                job.save()

                template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Reschedule.html')
                with open(template_path, 'r', encoding='utf-8') as template_file:
                    html_content = template_file.read()

                # Send email
                email_data = {
                    'email_subject': 'Interview Rescheduled',
                    'email_body': html_content,
                    'to_email': interview.user.email,
                    'context': {
                        'job': job.title,
                        'time': interview.interview_datetime,
                    },
                }
                send_normal_email(email_data)

                # Create notification
                notification_message = f'Your interview for the job {job.title} has been rescheduled to {interview.interview_datetime}.'
                Notification.objects.create(user=request.user, message=notification_message)

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class InterviewDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        interview = get_object_or_404(Interview, pk=kwargs['pk'], user=request.user)

        if interview.user != request.user:
            return Response({'error': 'You are not allowed to access this interview.'},
                            status=status.HTTP_403_FORBIDDEN)

        # Create notification
        notification_message = f"Your interview for the job '{interview.job.title}' scheduled on {interview.interview_datetime} has been deleted."
        Notification.objects.create(user=request.user, message=notification_message)


        template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Delete.html')
        with open(template_path, 'r', encoding='utf-8') as template_file:
            html_content = template_file.read()
        # Send email
        email_data = {
            'email_subject': 'Interview Deleted',
            'email_body': html_content,
            'to_email': interview.user.email,
            'context': {
                'job': interview.job.title,
            },
        }
        send_normal_email(email_data)

        interview.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class UserInterviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Filter interviews by the current user
        interviews = Interview.objects.filter(user=request.user)

        # Get the 'name' query parameter if provided
        name = request.query_params.get('name')
        if name is not None:
            interviews = interviews.filter(score__icontains=name)

        # Sort interviews by interview_datetime in descending order
        interviews = interviews.order_by('-interview_datetime')

        # Paginate the results
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of posts per page
        result_page = paginator.paginate_queryset(interviews, request)

        # Serialize the paginated results
        serializer = InterviewSerializer(result_page, many=True)

        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)



class PreparationMaterialDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        preparation_material = get_object_or_404(PreparationMaterial, id=id)
        job = preparation_material.job


        if preparation_material.ready == False:
            return Response({'detail': 'Your Material Is Not Ready Yet please come back later.'}, status=status.HTTP_409_CONFLICT)

        # Ensure the requesting user is the job owner
        if job.user != request.user:
            return Response({'detail': 'Not authorized to view this preparation material.'}, status=status.HTTP_403_FORBIDDEN)


        # Serialize the preparation material
        serializer = PreparationMaterialSerializer(preparation_material)
        response_data = serializer.data

        # Fetch and serialize associated objects
        response_data['blocks'] = PreparationBlockSerializer(preparation_material.blocks.all(), many=True).data
        response_data['google_search_results'] = GoogleSearchResultSerializer(preparation_material.blocks_2.all(), many=True).data
        response_data['coding_questions'] = CodingQuestionSerializer(preparation_material.coding_questions.all(), many=True).data
        response_data['youtube_links'] = YouTubeLinkSerializer(preparation_material.blocks_3.all(), many=True).data

        # Print the response data to the console
        print(response_data)

        return Response(response_data)






from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import google.generativeai as genai  # Import the generative AI module
from base.core_apis.google_search import search_google  # Import the search function
from base.core_apis.youtube import get_youtube_links # Import the search function
from base.core_apis.codestral_ai import call_chat_endpoint  # Import the codestral AI function
from base.core_apis.fetch_language import extract_language_from_answer  # Import the codestral AI function
import re



import threading
import uuid
import logging
from queue import Queue
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
 


from django.conf import settings

logger = logging.getLogger(__name__)
task_queue = Queue()

# # @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class PreparationMaterialCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             try:
#                 job_id, token, request = task_queue.get()
#                 self.process_task(job_id, token, request)
#             except ValueError as e:
#                 logger.error(f"Error unpacking values from queue: {e}")
#             except Exception as e:
#                 logger.error(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, job_id, token, request):
#         try:
#             job = Job.objects.get(id=job_id)
#             description = job.description
#             title = job.title

#             # Create a PreparationMaterial instance
#             preparation_material = PreparationMaterial.objects.create(job=job, title=f"Preparation for {title}")

#             # Prompt 1
#             prompt1 = f"Based on this {description}, will you need to write code or know about programming languages in this job? Answer YES or NO. Enclose your response in []."
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response1 = model.generate_content(prompt1)
#             content1 = response1._result.candidates[0].content.parts[0].text.strip()
#             print(content1)


#             # Prompt 3
#             prompt3 = f"Interview Preparation Tips for: {title}"

#             youtube_links = get_youtube_links(prompt3)
#             for yt_title, embed_url in youtube_links:
#                 YouTubeLink.objects.create(
#                     preparation_material=preparation_material,
#                     title=yt_title,
#                     embed_url=embed_url
#                 )

#             search_results = search_google(prompt3)
#             for result in search_results:
#                 GoogleSearchResult.objects.create(
#                     preparation_material=preparation_material,
#                     title=result['title'],
#                     snippet=result['snippet'],
#                     link=result['link']
#                 )

#             # Prompt 4
#             prompt4 = f"Based on this {description}, provide a set of questions and their answers at least ten of them to help in preparation of the related interview. Note The answer part should be very very detailed and start with the word Answer and the question should always have a question mark. write a question along with its answer at a time."
#             response4 = model.generate_content(prompt4)
#             content4 = response4._result.candidates[0].content.parts[0].text.strip()

#             # Extract questions and answers from content4
#             lines = content4.split('\n')
#             questions_and_answers = []
#             question = None
#             answer = None

#             for line in lines:
#                 if '?' in line.strip().lower():
#                     if question and answer:
#                         questions_and_answers.append((question, answer))
#                         answer = None
#                     question = line.strip()
#                 elif 'answer' in line.strip().lower():
#                     answer = line.strip()
#                 elif answer is not None:
#                     answer += ' ' + line.strip()

#             if question and answer:
#                 questions_and_answers.append((question, answer))

#             for q, a in questions_and_answers:
#                 PreparationBlock.objects.create(
#                     preparation_material=preparation_material,
#                     question=q,
#                     answer=a,
#                     score=0
#                 )
#             user_credits = request.user.credits
#             user = request.user
#             user.credits = user_credits - 30
#             user.save()

#             # If Prompt 1's response is "[YES]"
#             if content1 == "[YES]":
#                 user_credits = request.user.credits
#                 user = request.user
#                 user.credits = user_credits - 20
#                 user.save()
#                 prompt5 = f"Please provide me with some interview coding questions that include answers given as code snippets, for: {title}"
#                 data = {
#                     "model": "codestral-latest",
#                     "messages": [{"role": "user", "content": prompt5}]
#                 }

#                 codestral_response = call_chat_endpoint(data)
#                 if isinstance(codestral_response, dict):
#                     ai_response = codestral_response['choices'][0]['message']['content'].strip()
#                     lines = ai_response.split('\n')

#                     current_question = ""
#                     current_answer = ""
#                     current_language = ""
#                     in_answer = False

#                     for line in lines:
#                         if "Question:" in line:
#                             if current_question and current_answer:
#                                 current_language = extract_language_from_answer(current_answer)
#                                 CodingQuestion.objects.create(
#                                     preparation_material=preparation_material,
#                                     question=current_question,
#                                     answer=current_answer,
#                                     language=current_language
#                                 )
#                                 current_answer = ""
#                                 current_language = ""
#                             current_question = line.split("Question:")[1].strip()
#                             in_answer = False
#                         elif "Answer:" in line:
#                             in_answer = True
#                             current_answer = line.split("Answer:")[1].strip()
#                         elif in_answer:
#                             current_answer += '\n' + line.strip()

#                     if current_question and current_answer:
#                         current_language = extract_language_from_answer(current_answer)
#                         CodingQuestion.objects.create(
#                             preparation_material=preparation_material,
#                             question=current_question,
#                             answer=current_answer,
#                             language=current_language
#                         )

#             preparation_material.ready = True
#             preparation_material.save()
#             notification_message = f'Hey {request.user.username}, I finished making your prep resources please come for them'
#             Notification.objects.create(user=request.user, message=notification_message)

#         except Exception as e:
#             logger.error(f"Error processing task: {e}")

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         job_id = request.data.get('job_id')
#         if not job_id:
#             return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         job = get_object_or_404(Job, id=job_id, user=request.user)

#         # Generate and send token before analysis
#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         # Add the task to the queue
#         task_queue.put((job_id, token, request))

#         return response

@method_decorator(ratelimit(key='ip', rate='2/m', block=True), name='dispatch')
class PreparationMaterialCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def post(self, request, *args, **kwargs):
        if request.user.credits <= 50:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(Job, id=job_id, user=request.user)

        try:
            description = job.description
            title = job.title

            # Create a PreparationMaterial instance
            preparation_material = PreparationMaterial.objects.create(job=job, title=f"Preparation for {title}")

            # Prompt 1
            prompt1 = f"Based on this {description}, will you need to write code or know about programming languages in this job? Answer YES or NO. Enclose your response in []."
            model = genai.GenerativeModel('gemini-1.0-pro-latest')
            response1 = model.generate_content(prompt1)
            content1 = response1._result.candidates[0].content.parts[0].text.strip()
            print(content1)

            # Prompt 3
            prompt3 = f"Interview Preparation Tips for: {title}"

            youtube_links = get_youtube_links(prompt3)
            for yt_title, embed_url in youtube_links:
                YouTubeLink.objects.create(
                    preparation_material=preparation_material,
                    title=yt_title,
                    embed_url=embed_url
                )

            search_results = search_google(prompt3)
            for result in search_results:
                GoogleSearchResult.objects.create(
                    preparation_material=preparation_material,
                    title=result['title'],
                    snippet=result['snippet'],
                    link=result['link']
                )

            # Prompt 4
            prompt4 = f"Based on this {description}, provide a set of questions and their answers at least ten of them to help in preparation of the related interview. Note The answer part should be very very detailed and start with the word Answer and the question should always have a question mark. write a question along with its answer at a time."
            response4 = model.generate_content(prompt4)
            content4 = response4._result.candidates[0].content.parts[0].text.strip()

            # Extract questions and answers from content4
            lines = content4.split('\n')
            questions_and_answers = []
            question = None
            answer = None

            for line in lines:
                if '?' in line.strip().lower():
                    if question and answer:
                        questions_and_answers.append((question, answer))
                        answer = None
                    question = line.strip()
                elif 'answer' in line.strip().lower():
                    answer = line.strip()
                elif answer is not None:
                    answer += ' ' + line.strip()

            if question and answer:
                questions_and_answers.append((question, answer))

            for q, a in questions_and_answers:
                PreparationBlock.objects.create(
                    preparation_material=preparation_material,
                    question=q,
                    answer=a,
                    score=0
                )
            user_credits = request.user.credits
            user = request.user
            user.credits = user_credits - 30
            user.save()

            # If Prompt 1's response is "[YES]"
            if content1 == "[YES]":
                user_credits = request.user.credits
                user = request.user
                user.credits = user_credits - 20
                user.save()
                prompt5 = f"Please provide me with some interview coding questions that include answers given as code snippets, for: {title}"
                data = {
                    "model": "codestral-latest",
                    "messages": [{"role": "user", "content": prompt5}]
                }

                codestral_response = call_chat_endpoint(data)
                if isinstance(codestral_response, dict):
                    ai_response = codestral_response['choices'][0]['message']['content'].strip()
                    lines = ai_response.split('\n')

                    current_question = ""
                    current_answer = ""
                    current_language = ""
                    in_answer = False

                    for line in lines:
                        if "Question:" in line:
                            if current_question and current_answer:
                                current_language = extract_language_from_answer(current_answer)
                                CodingQuestion.objects.create(
                                    preparation_material=preparation_material,
                                    question=current_question,
                                    answer=current_answer,
                                    language=current_language
                                )
                                current_answer = ""
                                current_language = ""
                            current_question = line.split("Question:")[1].strip()
                            in_answer = False
                        elif "Answer:" in line:
                            in_answer = True
                            current_answer = line.split("Answer:")[1].strip()
                        elif in_answer:
                            current_answer += '\n' + line.strip()

                    if current_question and current_answer:
                        current_language = extract_language_from_answer(current_answer)
                        CodingQuestion.objects.create(
                            preparation_material=preparation_material,
                            question=current_question,
                            answer=current_answer,
                            language=current_language
                        )

            preparation_material.ready = True
            preparation_material.save()
            notification_message = f'Hey {request.user.username}, I finished making your prep resources, visit prep rooms to access them'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Preparation material created successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return Response({'detail': 'Error processing the preparation material.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PreparationMaterialDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(Job, id=job_id, user=request.user)
        preparation_material = get_object_or_404(PreparationMaterial, job=job)
        preparation_material.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# class PreparationBlockUpdateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request, *args, **kwargs):
#         block_id = kwargs.get('block_id')
#         if not block_id:
#             return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         block = get_object_or_404(PreparationBlock, id=block_id)
        
#         # Check if the user has permission to access this resource
#         if block.preparation_material.job.user != request.user:
#             return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        

#         # Get the answer from the request data
#         my_answer = request.data.get('my_answer')
#         if my_answer is None:
#             return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Update the answer field
#         block.my_answer = my_answer
#         block.save()
        
#         # Serialize and return the updated block
#         serializer = PreparationBlockSerializer(block)
#         return Response(serializer.data, status=status.HTTP_200_OK)


class PreparationBlockUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        block_id = kwargs.get('block_id')
        if not block_id:
            return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        block = get_object_or_404(PreparationBlock, id=block_id)
        
        # Check if the user has permission to access this resource
        if block.preparation_material.job.user != request.user:
            return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the block has already been attempted
        if block.attempted:
            return Response({'detail': 'You have already attempted this question.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field and set attempted to True
        block.my_answer = my_answer
        block.attempted = True
        block.save()
        
        # Serialize and return the updated block
        serializer = PreparationBlockSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)



# class CodingQuestionUpdateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request, *args, **kwargs):
#         block_id = kwargs.get('id')
#         if not block_id:
#             return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         block = get_object_or_404(CodingQuestion, id=block_id)
        
#         # Check if the user has permission to access this resource
#         if block.preparation_material.job.user != request.user:
#             return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        

#         # Get the answer from the request data
#         my_answer = request.data.get('my_answer')
#         if my_answer is None:
#             return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Update the answer field
#         block.my_answer = my_answer
#         block.save()
        
#         # Serialize and return the updated block
#         serializer = CodingQuestionSerializer(block)
#         return Response(serializer.data, status=status.HTTP_200_OK)

class CodingQuestionUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        block_id = kwargs.get('id')
        if not block_id:
            return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        block = get_object_or_404(CodingQuestion, id=block_id)
        
        # Check if the user has permission to access this resource
        if block.preparation_material.job.user != request.user:
            return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if the block has already been attempted
        if block.attempted:
            return Response({'detail': 'You have already attempted this question.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field and set attempted to True
        block.my_answer = my_answer
        block.attempted = True
        block.save()
        
        # Serialize and return the updated block
        serializer = CodingQuestionSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)







import time
from django.conf import settings

# @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class PreparationMaterialMarkingView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             material_id, token, request = task_queue.get()
#             try:
#                 self.process_task(material_id, token, request)
#             except Exception as e:
#                 logger.error(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, material_id, token, request):
#         preparation_material = get_object_or_404(PreparationMaterial, id=material_id)
#         blocks = PreparationBlock.objects.filter(preparation_material=preparation_material)
#         codes = CodingQuestion.objects.filter(preparation_material=preparation_material)

#         if not blocks.exists():
#             logger.error('No blocks found for this preparation material.')
#             return
#         print(f"Total number of blocks found: {blocks.count()}")

#         for block in blocks:
#             if not (block.question and block.answer):
#                 if not block.my_answer:
#                     block.my_answer = "i dont know!"
#                     block.save()
#                 logger.error(f'Block ID {block.id} is missing required fields.')
#                 return

#         scores = []
#         for block in blocks:
#             print(f"Marking block: {block.id}")

#             prompt = (
#                 f"Check the following block:\n\n"
#                 f"Question: {block.question}\n"
#                 f"My Answer: {block.my_answer}\n"
#                 f"Answer: {block.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer' in the context of the question. Note that 'Answer' is the correct answer provided in the marking scheme and 'My Answer' is the user's response.\n\n"
#                 "Please provide the score in the following format:\n\n"
#                 "Question {block.id}: <score>"
#             )
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response = model.generate_content(prompt)

#             try:
#                 score_text = response._result.candidates[0].content.parts[0].text.strip()
#                 print(f"Extracted score for block {block.id}: {score_text}")

#                 score = float(score_text.split(':')[-1].strip())
#                 block.score = score
#                 block.save()
#                 scores.append(f"Question {block.id}: {score_text}")
#             except Exception as e:
#                 logger.error(f"Error extracting score for block {block.id}: {e}")
#                 print(f"Error extracting score for block {block.id}: {e}")
#                 return

#             time.sleep(1)

#         print(scores)

#         if not codes.exists():
#             logger.error('No coding questions found for this preparation material.')

#         print(f"Total number of coding questions found: {codes.count()}")

#         code_scores = []
#         for code in codes:
#             if not (code.question and code.answer):
#                 if not code.my_answer:
#                     code.my_answer = "i dont know!"
#                     code.save()
#                 logger.error(f'Code ID {code.id} is missing required fields.')
#                 return

#         for code in codes:
#             print(f"Marking code: {code.id}")

#             code_prompt = (
#                 f"Check the following coding question:\n\n"
#                 f"Question: {code.question}\n"
#                 f"My Answer: {code.my_answer}\n"
#                 f"Answer: {code.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer' in the context of the question. Note that 'Answer' is the correct answer provided in the marking scheme and 'My Answer' is the user's response.\n\n"
#                 "Please provide the score in the following format ONLY: \n\n"
#                 "Question {code.id}: <score>"
#                 "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
#                 "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
#                 "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
#             )

#             data = {
#                 "model": "codestral-latest",
#                 "messages": [{"role": "user", "content": code_prompt}]
#             }

#             codestral_response = call_chat_endpoint(data)
#             ai_response = codestral_response['choices'][0]['message']['content'].strip()

#             try:
#                 match = re.search(r'Question\s+\d+:\s+(\d+)', ai_response)
#                 number = extract_first_number(ai_response)
#                 if number:
#                     code_score = float(number)
#                     print(f"Extracted score for coding question {code.id}: {code_score}")

#                     code.score = code_score
#                     code.save()
#                     code_scores.append(f"Question {code.id}: {ai_response}")
#                 else:
#                     raise ValueError("No numeric score found in response.")
#             except Exception as e:
#                 print(f"Error extracting score for coding question {code.id}: {e}")
#                 logger.error(f"Error extracting score for coding question {code.id}: {e}")
#                 return

#             time.sleep(1)
#         print(code_scores)

#         block_scores = PreparationBlock.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)
#         code_scores = CodingQuestion.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)

#         if not codes.exists():
#             all_scores = list(block_scores)
#         else:
#             all_scores = list(block_scores) + list(code_scores)

#         overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
#         print(overall_score)
#         preparation_material.score = overall_score
#         preparation_material.completed = True
#         preparation_material.save()
#         notification_message = f'Ola {request.user.username}, I am done marking the prep material you recently submitted , you can view your results in the prep section, you can make more prep materials always :) !'
#         Notification.objects.create(user=request.user, message=notification_message)

#         user_credits = request.user.credits
#         user = request.user
#         user.credits = user_credits - 50
#         user.save()

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         material_id = kwargs.get('material_id')
#         if not material_id:
#             return Response({'detail': 'Preparation Material ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         preparation_material = get_object_or_404(PreparationMaterial, id=material_id)

#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         task_queue.put((material_id, token, request))

#         return response



@method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
class PreparationMaterialMarkingView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def post(self, request, *args, **kwargs):
        if request.user.credits <= 50:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        material_id = kwargs.get('material_id')
        if not material_id:
            return Response({'detail': 'Preparation Material ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        preparation_material = get_object_or_404(PreparationMaterial, id=material_id)

        if preparation_material.completed:
            return Response({'detail': 'Material already marked.'}, status=status.HTTP_400_BAD_REQUEST)


        try:
            blocks = PreparationBlock.objects.filter(preparation_material=preparation_material)
            codes = CodingQuestion.objects.filter(preparation_material=preparation_material)

            if not blocks.exists():
                logger.error('No blocks found for this preparation material.')
                return Response({'detail': 'No blocks found for this preparation material.'}, status=status.HTTP_400_BAD_REQUEST)
            print(f"Total number of blocks found: {blocks.count()}")

            for block in blocks:
                if not (block.question and block.answer):
                    if not block.my_answer:
                        block.my_answer = "i dont know!"
                        block.save()
                    logger.error(f'Block ID {block.id} is missing required fields.')
                    return Response({'detail': f'Block ID {block.id} is missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

            scores = []
            for block in blocks:
                print(f"Marking block: {block.id}")

                prompt = (
                    f"Check the following block:\n\n"
                    f"Question: {block.question}\n"
                    f"My Answer: {block.my_answer}\n"
                    f"Answer: {block.answer}\n\n"
                    "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer' in the context of the question. Note that 'Answer' is the correct answer provided in the marking scheme and 'My Answer' is the user's response.\n\n"
                    "Please provide the score in the following format:\n\n"
                    "Question {block.id}: <score>"
                )
                model = genai.GenerativeModel('gemini-1.0-pro-latest')
                response = model.generate_content(prompt)

                try:
                    score_text = response._result.candidates[0].content.parts[0].text.strip()
                    print(f"Extracted score for block {block.id}: {score_text}")

                    score = float(score_text.split(':')[-1].strip())
                    block.score = score
                    block.save()
                    scores.append(f"Question {block.id}: {score_text}")
                except Exception as e:
                    logger.error(f"Error extracting score for block {block.id}: {e}")
                    print(f"Error extracting score for block {block.id}: {e}")
                    return Response({'detail': f"Error extracting score for block {block.id}: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                time.sleep(1)

            print(scores)

            if not codes.exists():
                logger.error('No coding questions found for this preparation material.')

            print(f"Total number of coding questions found: {codes.count()}")

            code_scores = []
            for code in codes:
                if not (code.question and code.answer):
                    if not code.my_answer:
                        code.my_answer = "i dont know!"
                        code.save()
                    logger.error(f'Code ID {code.id} is missing required fields.')
                    return Response({'detail': f'Code ID {code.id} is missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

            for code in codes:
                print(f"Marking code: {code.id}")

                code_prompt = (
                    f"Check the following coding question:\n\n"
                    f"Question: {code.question}\n"
                    f"My Answer: {code.my_answer}\n"
                    # f"Answer: {code.answer}\n\n"
                    "Assign a score from 1 to 100 based on how close 'My Answer' is in the context of the question. Note that 'My Answer' is the user's response.\n\n"
                    "Please provide the score in the following format ONLY: \n\n"
                    "Question {code.id}: <score>"
                    "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
                    "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
                    "AVOID ANY WORDS IN YOUR RESPONSE I JUST WANT SCORE STICK TO THIS FORMAT: Question {code.id}: <score>"
                )

                data = {
                    "model": "codestral-latest",
                    "messages": [{"role": "user", "content": code_prompt}]
                }

                codestral_response = call_chat_endpoint(data)
                ai_response = codestral_response['choices'][0]['message']['content'].strip()

                try:
                    match = re.search(r'Question\s+\d+:\s+(\d+)', ai_response)
                    number = extract_first_number(ai_response)
                    if number:
                        code_score = float(number)
                        print(f"Extracted score for coding question {code.id}: {code_score}")

                        code.score = code_score
                        code.save()
                        code_scores.append(f"Question {code.id}: {ai_response}")
                    else:
                        raise ValueError("No numeric score found in response.")
                except Exception as e:
                    print(f"Error extracting score for coding question {code.id}: {e}")
                    logger.error(f"Error extracting score for coding question {code.id}: {e}")
                    return Response({'detail': f"Error extracting score for coding question {code.id}: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                time.sleep(1)
            print(code_scores)

            block_scores = PreparationBlock.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)
            code_scores = CodingQuestion.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)

            if not codes.exists():
                all_scores = list(block_scores)
            else:
                all_scores = list(block_scores) + list(code_scores)

            overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
            print(overall_score)
            preparation_material.score = overall_score
            preparation_material.completed = True
            preparation_material.save()
            notification_message = f'Ola {request.user.username}, I am done marking the prep material you recently submitted , you can view your results in the prep section, you can make more prep materials always :) !'
            Notification.objects.create(user=request.user, message=notification_message)

            user_credits = request.user.credits
            user = request.user
            user.credits = user_credits - 50
            user.save()

            return Response({'detail': 'Preparation material marked successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return Response({'detail': 'Error processing the preparation material marking.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status

class InterviewRoomDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args):
        interview_session = get_object_or_404(InterviewSession, id=id)
        job = interview_session.interview.job

        if interview_session.ready == False:
            return Response({'detail': 'Your Material Is Not Ready Yet please come back later.'}, status=status.HTTP_409_CONFLICT)

        # Ensure the requesting user is the job owner
        if job.user != request.user:
            return Response({'detail': 'Not authorized to view this preparation material.'}, status=status.HTTP_403_FORBIDDEN)

        # Check if the session is expired
        if interview_session.expired:
            return Response({'detail': 'Sorry, your time is up. I am currently marking your work and will be in touch soon.'}, status=status.HTTP_403_FORBIDDEN)

        # Serialize the preparation material
        serializer = InterviewSessionSerializer(interview_session)
        response_data = serializer.data

        # Fetch and serialize associated objects without showing the answers
        blocks = InterviewBlockSerializer(interview_session.iblocks.all(), many=True).data
        for block in blocks:
            block.pop('answer', None)
        
        coding_questions = InterviewCodingQuestionSerializer(interview_session.icoding_questions.all(), many=True).data
        for question in coding_questions:
            question.pop('answer', None)
        
        response_data['blocks'] = blocks
        response_data['coding_questions'] = coding_questions

        # Print the response data to the console
        print(response_data)
    

        return Response(response_data)



# @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class InterviewRoomCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             job_id, token, request = task_queue.get()
#             try:
#                 self.process_task(job_id, token, request=request)
#             except Exception as e:
#                 logger.error(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, job_id, token, request):
#         try:    
            
#             interview = get_object_or_404(Interview, id=job_id)
#             print(f"Interview found: {interview}")

#             current_time = now()

            
#             description = interview.job.description
#             interview_session = InterviewSession.objects.create(interview=interview, start_time=current_time)

#             prompt1 = f"Based on this {description}, will you need to write code in the future? Answer YES or NO. Enclose your response in []."
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response1 = model.generate_content(prompt1)
#             if not hasattr(response1, '_result'):
#                 logger.error('Error generating AI response for prompt 1.')
#                 return
#             content1 = response1._result.candidates[0].content.parts[0].text.strip()
#             logger.info(f"AI Response for prompt 1: {content1}")
#             print(f"AI Response for prompt 1: {content1}")


#             questions_and_answers = []
#             for i in range(6):
#                 prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 80% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
#                 response4 = model.generate_content(prompt4)
#                 if not hasattr(response4, '_result'):
#                     logger.error(f'Error generating AI response for prompt 4, iteration {i + 1}.')
#                     return
#                 content4 = response4._result.candidates[0].content.parts[0].text.strip()
#                 logger.info(f"AI Response for prompt 4, iteration {i + 1}: {content4}")
#                 print(f"AI Response for prompt 4, iteration {i + 1}: {content4}")

#                 lines = content4.split('\n')
#                 question = ""
#                 answer = ""
#                 is_question = False
#                 is_answer = False

#                 for line in lines:
#                     stripped_line = line.strip()
#                     if not stripped_line:
#                         continue
#                     if 'question' in stripped_line.lower() and not is_question:
#                         question = stripped_line
#                         is_question = True
#                         is_answer = False
#                     elif 'answer' in stripped_line.lower() and is_question:
#                         answer = stripped_line
#                         is_answer = True
#                         is_question = False
#                     elif is_question:
#                         question += ' ' + stripped_line
#                     elif is_answer:
#                         answer += ' ' + stripped_line

#                 if question and answer:
#                     questions_and_answers.append((question, answer))

#                 time.sleep(1)


#             for q, a in questions_and_answers:
#                 InterviewBlock.objects.create(
#                     session=interview_session,
#                     question=q,
#                     answer=a,
#                     score=0
#                 )


#             logger.info(f"Extracted QA pairs: {questions_and_answers}")
#             print(f"Extracted QA pairs: {questions_and_answers}")
#             user_credits = request.user.credits
#             user = request.user
#             user.credits = user_credits - 30
#             user.save()

#             if content1 == "[YES]":
#                 questions_and_answers_coding = []
#                 for i in range(3):
#                     prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 90% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer' And please number the questions!!!!!!!!!!!!!!!!!!!!!"
#                     data = {
#                         "model": "codestral-latest",
#                         "messages": [{"role": "user", "content": prompt5}]
#                     }

#                     codestral_response = call_chat_endpoint(data)
#                     if isinstance(codestral_response, dict):
#                         ai_response = codestral_response['choices'][0]['message']['content'].strip()
#                         lines = ai_response.split('\n')
#                         current_question = ""
#                         current_answer = ""
#                         current_language = ""
#                         is_question = False
#                         is_answer = False

#                         for line in lines:
#                             stripped_line = line.strip()
#                             if not stripped_line:
#                                 continue
#                             if 'Question' in stripped_line and not is_question:
#                                 if current_question and current_answer:
#                                     current_language = extract_language_from_answer(current_answer)
#                                     questions_and_answers_coding.append((current_question, current_answer, current_language))
#                                     current_question = ""
#                                     current_answer = ""
#                                     current_language = ""
#                                 current_question = stripped_line
#                                 is_question = True
#                                 is_answer = False
#                             elif 'Answer' in stripped_line and is_question:
#                                 current_answer = stripped_line
#                                 is_answer = True
#                                 is_question = False
#                             elif is_question:
#                                 current_question += ' ' + stripped_line
#                             elif is_answer:
#                                 current_answer += ' ' + stripped_line

#                         if current_question and current_answer:
#                             current_language = extract_language_from_answer(current_answer)
#                             questions_and_answers_coding.append((current_question, current_answer, current_language))
                        
#                         print(f"Codestral AI Response: {ai_response}")
#                         user_credits = request.user.credits
#                         user = request.user
#                         user.credits = user_credits - 20
#                         user.save()

#                     else:
#                         print(f"Codestral AI Error: {codestral_response}")

#                     time.sleep(1)

#                 for q, a, lang in questions_and_answers_coding:
#                     InterviewCodingQuestion.objects.create(
#                         session=interview_session,
#                         question=q,
#                         answer=a,
#                         language=lang
#                     )
            
#             interview_session.ready = True
#             interview_session.save()
#             notification_message = f'Hi {request.user.username}, I am done preparing the interview meeting room please hurry and join!'
#             Notification.objects.create(user=request.user, message=notification_message)

#         except Exception as e:


#             print(f"Error processing task: {e}")



#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         job_id = request.data.get('job_id')
#         if not job_id:
#             return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview = get_object_or_404(Interview, id=job_id)
#         print(f"Interview found: {interview}")

#         current_time = now()


#         if interview.interview_datetime and current_time < interview.interview_datetime:
#                 logger.error('Cannot create a session earlier than the interview datetime.')
#                 return Response({'detail': 'Cannot create a session earlier than the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)


#         if interview.interview_datetime and current_time > interview.interview_datetime + timedelta(hours=5):
#             logger.error('Cannot create a session more than 5 hours past the interview datetime.')
#             return Response({'detail': 'Cannot create a session more than 5 hours past the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)


#         if InterviewSession.objects.filter(interview=interview).count() >= 2:
#             logger.error('Cannot create more than 2 sessions for the same interview.')
#             return Response({'detail': 'Cannot create more than 2 sessions for the same interview..'}, status=status.HTTP_400_BAD_REQUEST)


#         if InterviewSession.objects.filter(interview=interview, expired=False).exists():
#             logger.error('Cannot create a new session when there is an unexpired session for the same interview.')
#             return Response({'detail': 'Cannot create a new session when there is an unexpired session for the same interview.'}, status=status.HTTP_400_BAD_REQUEST)


#         current_time = now()
#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         task_queue.put((job_id, token, request))

#         return response

logger = logging.getLogger(__name__)
task_queue = Queue()


# @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class InterviewRoomCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             # Retrieve the three values from the queue
#             job_id, token, request = task_queue.get()
#             try:
#                 self.process_task(job_id, token, request=request)
#             except Exception as e:
#                 logger.error(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, job_id, token, request):
#         try:
#             interview = get_object_or_404(Interview, id=job_id)
#             print(f"Interview found: {interview}")

#             current_time = now()

#             description = interview.job.description
#             interview_session = InterviewSession.objects.create(interview=interview, start_time=current_time)

#             prompt1 = f"Based on this {description}, will you need to write code or know about programming languages in this job? Answer YES or NO. Enclose your response in []."
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response1 = model.generate_content(prompt1)
#             if not hasattr(response1, '_result'):
#                 logger.error('Error generating AI response for prompt 1.')
#                 return
#             content1 = response1._result.candidates[0].content.parts[0].text.strip()
#             logger.info(f"AI Response for prompt 1: {content1}")
#             print(f"AI Response for prompt 1: {content1}")

#             questions_and_answers = []
#             for i in range(6):
#                 prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 80% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
#                 response4 = model.generate_content(prompt4)
#                 if not hasattr(response4, '_result'):
#                     logger.error(f'Error generating AI response for prompt 4, iteration {i + 1}.')
#                     return
#                 content4 = response4._result.candidates[0].content.parts[0].text.strip()
#                 logger.info(f"AI Response for prompt 4, iteration {i + 1}: {content4}")
#                 print(f"AI Response for prompt 4, iteration {i + 1}: {content4}")

#                 lines = content4.split('\n')
#                 question = ""
#                 answer = ""
#                 is_question = False
#                 is_answer = False

#                 for line in lines:
#                     stripped_line = line.strip()
#                     if not stripped_line:
#                         continue
#                     if 'question' in stripped_line.lower() and not is_question:
#                         question = stripped_line
#                         is_question = True
#                         is_answer = False
#                     elif 'answer' in stripped_line.lower() and is_question:
#                         answer = stripped_line
#                         is_answer = True
#                         is_question = False
#                     elif is_question:
#                         question += ' ' + stripped_line
#                     elif is_answer:
#                         answer += ' ' + stripped_line

#                 if question and answer:
#                     questions_and_answers.append((question, answer))

#                 time.sleep(1)

#             for q, a in questions_and_answers:
#                 InterviewBlock.objects.create(
#                     session=interview_session,
#                     question=q,
#                     answer=a,
#                     score=0
#                 )

#             logger.info(f"Extracted QA pairs: {questions_and_answers}")
#             print(f"Extracted QA pairs: {questions_and_answers}")
#             user_credits = request.user.credits
#             user = request.user
#             user.credits = user_credits - 30
#             user.save()

#             if content1 == "[YES]":
#                 questions_and_answers_coding = []
#                 for i in range(3):
#                     prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 90% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer' And please number the questions!!!!!!!!!!!!!!!!!!!!!"
#                     data = {
#                         "model": "codestral-latest",
#                         "messages": [{"role": "user", "content": prompt5}]
#                     }

#                     codestral_response = call_chat_endpoint(data)
#                     if isinstance(codestral_response, dict):
#                         ai_response = codestral_response['choices'][0]['message']['content'].strip()
#                         lines = ai_response.split('\n')
#                         current_question = ""
#                         current_answer = ""
#                         current_language = ""
#                         is_question = False
#                         is_answer = False

#                         for line in lines:
#                             stripped_line = line.strip()
#                             if not stripped_line:
#                                 continue
#                             if 'Question' in stripped_line and not is_question:
#                                 if current_question and current_answer:
#                                     current_language = extract_language_from_answer(current_answer)
#                                     questions_and_answers_coding.append((current_question, current_answer, current_language))
#                                     current_question = ""
#                                     current_answer = ""
#                                     current_language = ""
#                                 current_question = stripped_line
#                                 is_question = True
#                                 is_answer = False
#                             elif 'Answer' in stripped_line and is_question:
#                                 current_answer = stripped_line
#                                 is_answer = True
#                                 is_question = False
#                             elif is_question:
#                                 current_question += ' ' + stripped_line
#                             elif is_answer:
#                                 current_answer += ' ' + stripped_line

#                         if current_question and current_answer:
#                             current_language = extract_language_from_answer(current_answer)
#                             questions_and_answers_coding.append((current_question, current_answer, current_language))

#                         print(f"Codestral AI Response: {ai_response}")
#                         user_credits = request.user.credits
#                         user = request.user
#                         user.credits = user_credits - 20
#                         user.save()

#                     else:
#                         print(f"Codestral AI Error: {codestral_response}")

#                     time.sleep(1)

#                 for q, a, lang in questions_and_answers_coding:
#                     InterviewCodingQuestion.objects.create(
#                         session=interview_session,
#                         question=q,
#                         answer=a,
#                         language=lang
#                     )

#             interview_session.ready = True
#             interview_session.save()
#             notification_message = f'Hi {request.user.username}, I am done preparing the interview meeting room please hurry and join!'
#             Notification.objects.create(user=request.user, message=notification_message)

#         except Exception as e:
#             print(f"Error processing task: {e}")

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         job_id = request.data.get('job_id')
#         if not job_id:
#             return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview = get_object_or_404(Interview, id=job_id)
#         print(f"Interview found: {interview}")

#         current_time = now()

#         if interview.interview_datetime and current_time < interview.interview_datetime:
#             logger.error('Cannot create a session earlier than the interview datetime.')
#             return Response({'detail': 'Cannot create a session earlier than the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

#         if interview.interview_datetime and current_time > interview.interview_datetime + timedelta(hours=5):
#             logger.error('Cannot create a session more than 5 hours after the interview datetime.')
#             return Response({'detail': 'Cannot create a session more than 5 hours after the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

#         token = self.generate_token()

#         task_queue.put((job_id, token, request))
#         logger.info(f'Task added to the queue with job_id: {job_id}, token: {token}')

#         return Response({'message': 'Task added to queue. Processing will start soon.', 'token': token})



# @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class InterviewRoomCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         job_id = request.data.get('job_id')
#         if not job_id:
#             return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview = get_object_or_404(Interview, id=job_id)
#         print(f"Interview found: {interview}")

#         current_time = now()

#         if interview.interview_datetime and current_time < interview.interview_datetime:
#             logger.error('Cannot create a session earlier than the interview datetime.')
#             return Response({'detail': 'Cannot create a session earlier than the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

#         if interview.interview_datetime and current_time > interview.interview_datetime + timedelta(hours=5):
#             logger.error('Cannot create a session more than 5 hours after the interview datetime.')
#             return Response({'detail': 'Cannot create a session more than 5 hours after the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             description = interview.job.description
#             interview_session = InterviewSession.objects.create(interview=interview, start_time=current_time)

#             prompt1 = f"Based on this {description}, will you need to write code or know about programming languages in this job? Answer YES or NO. Enclose your response in []."
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response1 = model.generate_content(prompt1)
#             if not hasattr(response1, '_result'):
#                 logger.error('Error generating AI response for prompt 1.')
#                 return Response({'detail': 'Error generating AI response for prompt 1.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             content1 = response1._result.candidates[0].content.parts[0].text.strip()
#             logger.info(f"AI Response for prompt 1: {content1}")
#             print(f"AI Response for prompt 1: {content1}")

#             questions_and_answers = []
#             for i in range(6):
#                 prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 80% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
#                 response4 = model.generate_content(prompt4)
#                 if not hasattr(response4, '_result'):
#                     logger.error(f'Error generating AI response for prompt 4, iteration {i + 1}.')
#                     return Response({'detail': f'Error generating AI response for prompt 4, iteration {i + 1}.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#                 content4 = response4._result.candidates[0].content.parts[0].text.strip()
#                 logger.info(f"AI Response for prompt 4, iteration {i + 1}: {content4}")
#                 print(f"AI Response for prompt 4, iteration {i + 1}: {content4}")

#                 lines = content4.split('\n')
#                 question = ""
#                 answer = ""
#                 is_question = False
#                 is_answer = False

#                 for line in lines:
#                     stripped_line = line.strip()
#                     if not stripped_line:
#                         continue
#                     if 'question' in stripped_line.lower() and not is_question:
#                         question = stripped_line
#                         is_question = True
#                         is_answer = False
#                     elif 'answer' in stripped_line.lower() and is_question:
#                         answer = stripped_line
#                         is_answer = True
#                         is_question = False
#                     elif is_question:
#                         question += ' ' + stripped_line
#                     elif is_answer:
#                         answer += ' ' + stripped_line

#                 if question and answer:
#                     questions_and_answers.append((question, answer))

#                 time.sleep(1)

#             for q, a in questions_and_answers:
#                 InterviewBlock.objects.create(
#                     session=interview_session,
#                     question=q,
#                     answer=a,
#                     score=0
#                 )

#             logger.info(f"Extracted QA pairs: {questions_and_answers}")
#             print(f"Extracted QA pairs: {questions_and_answers}")
#             user_credits = request.user.credits
#             user = request.user
#             user.credits = user_credits - 30
#             user.save()

#             if content1 == "[YES]":
#                 questions_and_answers_coding = []
#                 for i in range(3):
#                     prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 90% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer' And please number the questions!!!!!!!!!!!!!!!!!!!!!"
#                     data = {
#                         "model": "codestral-latest",
#                         "messages": [{"role": "user", "content": prompt5}]
#                     }

#                     codestral_response = call_chat_endpoint(data)
#                     if isinstance(codestral_response, dict):
#                         ai_response = codestral_response['choices'][0]['message']['content'].strip()
#                         lines = ai_response.split('\n')
#                         current_question = ""
#                         current_answer = ""
#                         current_language = ""
#                         is_question = False
#                         is_answer = False

#                         for line in lines:
#                             stripped_line = line.strip()
#                             if not stripped_line:
#                                 continue
#                             if 'Question' in stripped_line and not is_question:
#                                 if current_question and current_answer:
#                                     current_language = extract_language_from_answer(current_answer)
#                                     questions_and_answers_coding.append((current_question, current_answer, current_language))
#                                     current_question = ""
#                                     current_answer = ""
#                                     current_language = ""
#                                 current_question = stripped_line
#                                 is_question = True
#                                 is_answer = False
#                             elif 'Answer' in stripped_line and is_question:
#                                 current_answer = stripped_line
#                                 is_answer = True
#                                 is_question = False
#                             elif is_question:
#                                 current_question += ' ' + stripped_line
#                             elif is_answer:
#                                 current_answer += ' ' + stripped_line

#                         if current_question and current_answer:
#                             current_language = extract_language_from_answer(current_answer)
#                             questions_and_answers_coding.append((current_question, current_answer, current_language))

#                         print(f"Codestral AI Response: {ai_response}")
#                         user_credits = request.user.credits
#                         user = request.user
#                         user.credits = user_credits - 20
#                         user.save()

#                     else:
#                         print(f"Codestral AI Error: {codestral_response}")

#                     time.sleep(1)

#                 for q, a, lang in questions_and_answers_coding:
#                     InterviewCodingQuestion.objects.create(
#                         session=interview_session,
#                         question=q,
#                         answer=a,
#                         language=lang
#                     )

#             interview_session.ready = True
#             interview_session.save()
#             notification_message = f'Hi {request.user.username}, I am done preparing the interview meeting room please hurry and join!'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Interview room created successfully.'}, status=status.HTTP_200_OK)

#         except Exception as e:
#             logger.error(f"Error processing task: {e}")
#             return Response({'detail': 'Error processing the interview room creation.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
class InterviewRoomCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def post(self, request, *args, **kwargs):
        if request.user.credits <= 50:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user has an active session
        active_session = InterviewSession.objects.filter(interview__user=request.user, ready=True, marked=False).first()
        if active_session:
            return Response({'detail': 'You still have an active session.'}, status=status.HTTP_400_BAD_REQUEST)

        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        interview = get_object_or_404(Interview, id=job_id)
        print(f"Interview found: {interview}")

        current_time = now()

        if interview.interview_datetime and current_time < interview.interview_datetime:
            logger.error('Cannot create a session earlier than the interview datetime.')
            return Response({'detail': 'Cannot create a session earlier than the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

        if interview.interview_datetime and current_time > interview.interview_datetime + timedelta(hours=5):
            logger.error('Cannot create a session more than 5 hours after the interview datetime.')
            return Response({'detail': 'Cannot create a session more than 5 hours after the interview datetime.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            description = interview.job.description
            interview_session = InterviewSession.objects.create(interview=interview, start_time=current_time)

            prompt1 = f"Based on this {description}, will you need to write code or know about programming languages in this job? Answer YES or NO. Enclose your response in []."
            model = genai.GenerativeModel('gemini-1.0-pro-latest')
            response1 = model.generate_content(prompt1)
            if not hasattr(response1, '_result'):
                logger.error('Error generating AI response for prompt 1.')
                return Response({'detail': 'Error generating AI response for prompt 1.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            content1 = response1._result.candidates[0].content.parts[0].text.strip()
            logger.info(f"AI Response for prompt 1: {content1}")
            print(f"AI Response for prompt 1: {content1}")

            questions_and_answers = []
            for i in range(6):
                prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 10% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
                response4 = model.generate_content(prompt4)
                if not hasattr(response4, '_result'):
                    logger.error(f'Error generating AI response for prompt 4, iteration {i + 1}.')
                    return Response({'detail': f'Error generating AI response for prompt 4, iteration {i + 1}.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                content4 = response4._result.candidates[0].content.parts[0].text.strip()
                logger.info(f"AI Response for prompt 4, iteration {i + 1}: {content4}")
                print(f"AI Response for prompt 4, iteration {i + 1}: {content4}")

                lines = content4.split('\n')
                question = ""
                answer = ""
                is_question = False
                is_answer = False

                for line in lines:
                    stripped_line = line.strip()
                    if not stripped_line:
                        continue
                    if 'question' in stripped_line.lower() and not is_question:
                        question = stripped_line
                        is_question = True
                        is_answer = False
                    elif 'answer' in stripped_line.lower() and is_question:
                        answer = stripped_line
                        is_answer = True
                        is_question = False
                    elif is_question:
                        question += ' ' + stripped_line
                    elif is_answer:
                        answer += ' ' + stripped_line

                if question and answer:
                    questions_and_answers.append((question, answer))

                time.sleep(1)

            for q, a in questions_and_answers:
                InterviewBlock.objects.create(
                    session=interview_session,
                    question=q,
                    answer=a,
                    score=0
                )

            logger.info(f"Extracted QA pairs: {questions_and_answers}")
            print(f"Extracted QA pairs: {questions_and_answers}")
            user_credits = request.user.credits
            user = request.user
            user.credits = user_credits - 30
            user.save()

            if content1 == "[YES]":
                questions_and_answers_coding = []
                for i in range(3):
                    prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 10% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer' And please number the questions!!!!!!!!!!!!!!!!!!!!!"
                    data = {
                        "model": "codestral-latest",
                        "messages": [{"role": "user", "content": prompt5}]
                    }

                    codestral_response = call_chat_endpoint(data)
                    if isinstance(codestral_response, dict):
                        ai_response = codestral_response['choices'][0]['message']['content'].strip()
                        lines = ai_response.split('\n')
                        current_question = ""
                        current_answer = ""
                        current_language = ""
                        is_question = False
                        is_answer = False

                        for line in lines:
                            stripped_line = line.strip()
                            if not stripped_line:
                                continue
                            if 'Question' in stripped_line and not is_question:
                                if current_question and current_answer:
                                    current_language = extract_language_from_answer(current_answer)
                                    questions_and_answers_coding.append((current_question, current_answer, current_language))
                                    current_question = ""
                                    current_answer = ""
                                    current_language = ""
                                current_question = stripped_line
                                is_question = True
                                is_answer = False
                            elif 'Answer' in stripped_line and is_question:
                                current_answer = stripped_line
                                is_answer = True
                                is_question = False
                            elif is_question:
                                current_question += ' ' + stripped_line
                            elif is_answer:
                                current_answer += ' ' + stripped_line

                        if current_question and current_answer:
                            current_language = extract_language_from_answer(current_answer)
                            questions_and_answers_coding.append((current_question, current_answer, current_language))

                        print(f"Codestral AI Response: {ai_response}")
                        user_credits = request.user.credits
                        user = request.user
                        user.credits = user_credits - 20
                        user.save()

                    else:
                        print(f"Codestral AI Error: {codestral_response}")

                    time.sleep(1)

                for q, a, lang in questions_and_answers_coding:
                    InterviewCodingQuestion.objects.create(
                        session=interview_session,
                        question=q,
                        answer=a,
                        language=lang
                    )

            interview_session.ready = True
            interview_session.save()
            notification_message = f'Hi {request.user.username}, I am done preparing the interview meeting room please hurry and join!'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Interview room created successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return Response({'detail': 'Error processing the interview room creation.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from asgiref.sync import sync_to_async
import time
from .tasks import create_interview_session_task

 














class InterviewBlockUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        block_id = kwargs.get('block_id')
        if not block_id:
            return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        block = get_object_or_404(InterviewBlock, id=block_id)
        
        # Check if the user has permission to access this resource
        if block.session.interview.user != request.user:
            return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        

        if block.session.expired:
            return Response({'detail': 'Your session expired feel free to make a new one, i am currently marking your work'}, status=status.HTTP_403_FORBIDDEN)


        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field
        block.my_answer = my_answer
        block.save()
        
        # Serialize and return the updated block
        serializer = InterviewBlockSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)








class InterviewCodingQuestionUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        block_id = kwargs.get('id')
        if not block_id:
            return Response({'detail': 'Block ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        block = get_object_or_404(InterviewCodingQuestion, id=block_id)
        
        # Check if the user has permission to access this resource
        if block.session.interview.user != request.user:
            return Response({'detail': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        

        if block.session.expired:
            return Response({'detail': f'Your session expired feel free to make a new one in future i am currently assesing your work'}, status=status.HTTP_403_FORBIDDEN)


        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field
        block.my_answer = my_answer
        block.save()
        
        # Serialize and return the updated block
        serializer = InterviewCodingQuestionSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)








# # @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class InterviewRoomMarkingView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             material_id, token, request = task_queue.get()
#             try:
#                 self.process_task(material_id, token, request=request)
#             except Exception as e:
#                 print(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, material_id, token, request):
#         interview_session = get_object_or_404(InterviewSession, id=material_id)
#         blocks = InterviewBlock.objects.filter(session=interview_session)
#         codes = InterviewCodingQuestion.objects.filter(session=interview_session)

       
#         scores = []
#         for block in blocks:
#             print(f"Marking block: {block.id}")

#             prompt = (
#                 f"Check the following block:\n\n"
#                 f"Question: {block.question}\n"
#                 f"My Answer: {block.my_answer}\n"
#                 f"Answer: {block.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer' in the context of the question whether it is a valid response to the question. Note that 'Answer' is the correct answer provided in the marking scheme and 'My Answer' is the user's response.\n\n"
#                 "So Please dont give out generous marls ensure 'My Answer' answers the 'Question' correctly if not just AWARD A ZERO FOR A RESPONSE FAR FROM THE 'ANSWER'!!!\n\n"
#                 "Please be very very strict in marking and awarding score. For instance, if they are very far apart, just give 0. Keep it simple:\n\n"
#                 "THINK VERY CAREFULLY THROUGH THE INSTRUCTIONS BEFORE ASSIGNING A SCORE !!!!!!!!!!!!!!!! \n\n"
#                 "Please provide the score in the following format:\n\n"
#                 f"Question {block.id}: <score>"
#             )
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response = model.generate_content(prompt)

#             try:
#                 score_text = response._result.candidates[0].content.parts[0].text.strip()
#                 print(f"Extracted score for block {block.id}: {score_text}")

#                 score = float(score_text.split(':')[-1].strip())
#                 block.score = score
#                 block.save()
#                 scores.append(f"Question {block.id}: {score_text}")
#             except Exception as e:
#                 print(f"Error extracting score for block {block.id}: {e}")
#                 print(f"Error extracting score for block {block.id}: {e}")
#                 return

#             time.sleep(1)

#         print(scores)

#         if not codes.exists():
#             print('No coding questions found for this preparation material.')

#         print(f"Total number of coding questions found: {codes.count()}")

#         code_scores = []
#         for code in codes:
#             if not code.my_answer:
#                 code.my_answer = "I don't know"
#                 code.save()
#             if not (code.question and code.answer):
#                 print(f'Code ID {code.id} is missing required fields.')
#                 return

#         for code in codes:
#             print(f"Marking code: {code.id}")

#             code_prompt = (
#                 f"Check the following coding question:\n\n"
#                 f"My Answer: {code.my_answer}\n"
#                 f"Answer: {code.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
#                 "Please provide the score in the following format ONLY: \n\n"
#                 f"Question {code.id}: <score>"
#                 "AVOID ANY WORDS IN YOUR RESPONSE. I JUST WANT THE SCORE. STICK TO THIS FORMAT: Question {code.id}: <score>"
#             )

#             data = {
#                 "model": "codestral-latest",
#                 "messages": [{"role": "user", "content": code_prompt}]
#             }

#             codestral_response = call_chat_endpoint(data)
#             ai_response = codestral_response['choices'][0]['message']['content'].strip()

#             try:
#                 match = re.search(r'Question\s+\d+:\s+(\d+)', ai_response)
#                 number = extract_first_number(ai_response)
#                 if number:
#                     code_score = float(number)
#                     print(f"Extracted score for coding question {code.id}: {code_score}")

#                     code.score = code_score
#                     code.save()
#                     code_scores.append(f"Question {code.id}: {ai_response}")
#                 else:
#                     raise ValueError("No numeric score found in response.")
#             except Exception as e:
#                 print(f"Error extracting score for coding question {code.id}: {e}")
#                 print(f"Error extracting score for coding question {code.id}: {e}")
#                 return

#             time.sleep(1)
#         print(code_scores)

#         block_scores = InterviewBlock.objects.filter(session=interview_session).values_list('score', flat=True)
#         code_scores = InterviewCodingQuestion.objects.filter(session=interview_session).values_list('score', flat=True)

#         all_scores = list(block_scores) + list(code_scores)
#         overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

#         interview_session.score = overall_score
#         interview_session.marked = True
#         interview_session.save()
#         notification_message = f'Hello there {request.user.username}, congratulations on finishing your interview session please check your email to see how you perfomed , you are free to make one more interview session for this job but it has to be within 5 hours from now:)!'
#         Notification.objects.create(user=request.user, message=notification_message)
#         template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Mark.html')
#         with open(template_path, 'r', encoding='utf-8') as template_file:
#             html_content = template_file.read()
#         email_data = {
#             'email_subject': 'Your Interview Results',
#             'email_body': html_content,
#             'to_email': request.user.email,
#             'context': {
#                 'score': overall_score,
#             },
#         }
#         send_normal_email(email_data)


#         user_credits = request.user.credits
#         user_csessions = request.user.csessions
#         user_passed = request.user.passed
#         user_failed = request.user.failed

#         if overall_score > 50 :
#             user = request.user
#             user.passed = user_passed + 1
#             user.save()
#         else:
#             user = request.user
#             user.failed = user_failed + 1
#             user.save()
           


#         user = request.user
#         user.credits = user_credits - 50
#         user.csessions = user_csessions + 1

#         user.save()

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#                 notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#                 Notification.objects.create(user=request.user, message=notification_message)

#                 return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         material_id = kwargs.get('material_id')
#         if not material_id:
#             return Response({'detail': 'Interview Session ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview_session = get_object_or_404(InterviewSession, id=material_id)
#         blocks = InterviewBlock.objects.filter(session=interview_session)
#         codes = InterviewCodingQuestion.objects.filter(session=interview_session)


#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         task_queue.put((material_id, token, request))

#         return response


# @method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
# class InterviewRoomMarkingView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             material_id, token, request = task_queue.get()
#             try:
#                 self.process_task(material_id, token, request=request)
#             except Exception as e:
#                 print(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, material_id, token, request):
#         interview_session = get_object_or_404(InterviewSession, id=material_id)
#         blocks = InterviewBlock.objects.filter(session=interview_session)
#         codes = InterviewCodingQuestion.objects.filter(session=interview_session)

       
#         scores = []
#         for block in blocks:
#             print(f"Marking block: {block.id}")

#             prompt = (
#                 f"Check the following block:\n\n"
#                 f"My Answer: {block.my_answer}\n"
#                 f"Answer: {block.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
#                 "Please be very very strict in marking and awarding scores. For instance, if they are very far apart, just give 0. Keep it simple:\n\n"
#                 "Please provide the score in the following format:\n\n"
#                 f"Question {block.id}: <score>"
#             )
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response = model.generate_content(prompt)

#             try:
#                 score_text = response._result.candidates[0].content.parts[0].text.strip()
#                 print(f"Extracted score for block {block.id}: {score_text}")

#                 score = float(score_text.split(':')[-1].strip())
#                 block.score = score
#                 block.save()
#                 scores.append(f"Question {block.id}: {score_text}")
#             except Exception as e:
#                 print(f"Error extracting score for block {block.id}: {e}")
#                 print(f"Error extracting score for block {block.id}: {e}")
#                 return

#             time.sleep(1)

#         print(scores)

#         if not codes.exists():
#             print('No coding questions found for this preparation material.')

#         print(f"Total number of coding questions found: {codes.count()}")

#         code_scores = []
#         for code in codes:
#             if not code.my_answer:
#                 code.my_answer = "I don't know"
#                 code.save()
#             if not (code.question and code.answer):
#                 print(f'Code ID {code.id} is missing required fields.')
#                 return

#         for code in codes:
#             print(f"Marking code: {code.id}")

#             code_prompt = (
#                 f"Check the following coding question:\n\n"
#                 f"My Answer: {code.my_answer}\n"
#                 f"Answer: {code.answer}\n\n"
#                 "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
#                 "Please provide the score in the following format ONLY: \n\n"
#                 f"Question {code.id}: <score>"
#                 "AVOID ANY WORDS IN YOUR RESPONSE. I JUST WANT THE SCORE. STICK TO THIS FORMAT: Question {code.id}: <score>"
#             )

#             data = {
#                 "model": "codestral-latest",
#                 "messages": [{"role": "user", "content": code_prompt}]
#             }

#             codestral_response = call_chat_endpoint(data)
#             ai_response = codestral_response['choices'][0]['message']['content'].strip()

#             try:
#                 match = re.search(r'Question\s+\d+:\s+(\d+)', ai_response)
#                 number = extract_first_number(ai_response)
#                 if number:
#                     code_score = float(number)
#                     print(f"Extracted score for coding question {code.id}: {code_score}")

#                     code.score = code_score
#                     code.save()
#                     code_scores.append(f"Question {code.id}: {ai_response}")
#                 else:
#                     raise ValueError("No numeric score found in response.")
#             except Exception as e:
#                 print(f"Error extracting score for coding question {code.id}: {e}")
#                 print(f"Error extracting score for coding question {code.id}: {e}")
#                 return

#             time.sleep(1)
#         print(code_scores)

#         block_scores = InterviewBlock.objects.filter(session=interview_session).values_list('score', flat=True)
#         code_scores = InterviewCodingQuestion.objects.filter(session=interview_session).values_list('score', flat=True)

#         all_scores = list(block_scores) + list(code_scores)
#         overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

#         interview_session.score = overall_score
#         interview_session.marked = True
#         interview_session.save()
#         notification_message = f'Hello there {request.user.username}, congratulations on finishing your interview session please head on to your email to see how you perfomed , you are free to make one more interview session for this job but it has to be within 5 hours from now:)!'
#         Notification.objects.create(user=request.user, message=notification_message)

#         template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Mark.html')
#         with open(template_path, 'r', encoding='utf-8') as template_file:
#             html_content = template_file.read()
#         email_data = {
#             'email_subject': 'Your Interview Results',
#             'email_body': html_content,
#             'to_email': request.user.email,
#             'context': {
#                 'score': overall_score,
#             },
#         }
#         send_normal_email(email_data)


#         user_credits = request.user.credits
#         user_csessions = request.user.csessions
#         user_passed = request.user.passed
#         user_failed = request.user.failed

#         if overall_score > 50 :
#             user = request.user
#             user.passed = user_passed + 1
#             user.save()
#         else:
#             user = request.user
#             user.failed = user_failed + 1
#             user.save()
           


#         user = request.user
#         user.credits = user_credits - 50
#         user.csessions = user_csessions + 1

#         user.save()

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         if request.user.credits <= 50:
#                 notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#                 Notification.objects.create(user=request.user, message=notification_message)

#                 return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         material_id = kwargs.get('material_id')
#         if not material_id:
#             return Response({'detail': 'Interview Session ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         interview_session = get_object_or_404(InterviewSession, id=material_id)
#         blocks = InterviewBlock.objects.filter(session=interview_session)
#         codes = InterviewCodingQuestion.objects.filter(session=interview_session)


#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         task_queue.put((material_id, token, request))

#         return response

@method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
class InterviewRoomMarkingView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def post(self, request, *args, **kwargs):
        if request.user.credits <= 50:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error you are out of credits upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        material_id = kwargs.get('material_id')
        if not material_id:
            return Response({'detail': 'Interview Session ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        interview_session = get_object_or_404(InterviewSession, id=material_id)
        blocks = InterviewBlock.objects.filter(session=interview_session)
        codes = InterviewCodingQuestion.objects.filter(session=interview_session)

        if interview_session.marked:
            return Response({'detail': 'Session already marked.'}, status=status.HTTP_200_OK)


        try:
            scores = []
            for block in blocks:
                print(f"Marking block: {block.id}")

                prompt = (
                    f"Check the following block:\n\n"
                    f"My Answer: {block.my_answer}\n"
                    f"Answer: {block.answer}\n\n"
                    "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
                    "Please be strict in marking and awarding scores. For instance, if they are very far apart, just give 0. Keep it simple:\n\n"
                    "Please provide the score in the following format:\n\n"
                    f"Question {block.id}: <score>"
                )
                model = genai.GenerativeModel('gemini-1.0-pro-latest')
                response = model.generate_content(prompt)

                try:
                    score_text = response._result.candidates[0].content.parts[0].text.strip()
                    print(f"Extracted score for block {block.id}: {score_text}")

                    score = float(score_text.split(':')[-1].strip())
                    block.score = score
                    block.save()
                    scores.append(f"Question {block.id}: {score_text}")
                except Exception as e:
                    logger.error(f"Error extracting score for block {block.id}: {e}")
                    print(f"Error extracting score for block {block.id}: {e}")
                    return Response({'detail': f"Error extracting score for block {block.id}: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                time.sleep(1)

            print(scores)

            if not codes.exists():
                print('No coding questions found for this preparation material.')

            print(f"Total number of coding questions found: {codes.count()}")

            code_scores = []
            for code in codes:
                if not code.my_answer:
                    code.my_answer = "I don't know"
                    code.save()
                if not (code.question and code.answer):
                    print(f'Code ID {code.id} is missing required fields.')
                    return Response({'detail': f'Code ID {code.id} is missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

            for code in codes:
                print(f"Marking code: {code.id}")

                code_prompt = (
                    f"Check the following coding question:\n\n"
                    f"My Answer: {code.my_answer}\n"
                    f"Answer: {code.answer}\n\n"
                    "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
                    "Please provide the score in the following format ONLY: \n\n"
                    f"Question {code.id}: <score>"
                    "AVOID ANY WORDS IN YOUR RESPONSE. I JUST WANT THE SCORE. STICK TO THIS FORMAT: Question {code.id}: <score>"
                )

                data = {
                    "model": "codestral-latest",
                    "messages": [{"role": "user", "content": code_prompt}]
                }

                codestral_response = call_chat_endpoint(data)
                ai_response = codestral_response['choices'][0]['message']['content'].strip()

                try:
                    match = re.search(r'Question\s+\d+:\s+(\d+)', ai_response)
                    number = extract_first_number(ai_response)
                    if number:
                        code_score = float(number)
                        print(f"Extracted score for coding question {code.id}: {code_score}")

                        code.score = code_score
                        code.save()
                        code_scores.append(f"Question {code.id}: {ai_response}")
                    else:
                        raise ValueError("No numeric score found in response.")
                except Exception as e:
                    logger.error(f"Error extracting score for coding question {code.id}: {e}")
                    print(f"Error extracting score for coding question {code.id}: {e}")
                    return Response({'detail': f"Error extracting score for coding question {code.id}: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                time.sleep(1)
            print(code_scores)

            block_scores = InterviewBlock.objects.filter(session=interview_session).values_list('score', flat=True)
            code_scores = InterviewCodingQuestion.objects.filter(session=interview_session).values_list('score', flat=True)

            all_scores = list(block_scores) + list(code_scores)
            overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

            interview_session.score = overall_score
            interview_session.marked = True
            interview_session.save()
            notification_message = f'Hello there {request.user.username}, congratulations on finishing your interview session please head on to your email to see how you performed , you are free to make one more interview session for this job but it has to be within 5 hours from now:)!'
            Notification.objects.create(user=request.user, message=notification_message)

            template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Mark.html')
            with open(template_path, 'r', encoding='utf-8') as template_file:
                html_content = template_file.read()
            email_data = {
                'email_subject': 'Your Interview Results',
                'email_body': html_content,
                'to_email': request.user.email,
                'context': {
                    'score': overall_score,
                },
            }
            send_normal_email(email_data)

            user_credits = request.user.credits
            user_csessions = request.user.csessions
            user_passed = request.user.passed
            user_failed = request.user.failed

            if overall_score > 50:
                user = request.user
                user.passed = user_passed + 1
                user.save()
            else:
                user = request.user
                user.failed = user_failed + 1
                user.save()

            user = request.user
            user.credits = user_credits - 50
            user.csessions = user_csessions + 1
            user.save()

            return Response({'detail': 'Interview session marked successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return Response({'detail': 'Error processing the interview session marking.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





from .tasks import mark_interview_room

from base.models import Asisstant
from base.serializers import AsisstantSerializer




class GetAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            # Check if the user has an Agent object
            agent = Asisstant.objects.filter(session__interview__user=request.user).first()

            if agent:
                # Serialize and return the Agent object
                serializer = AsisstantSerializer(agent)
                if agent.ready == False:
                    print(agent.id)
                    print(agent.ready)
                    print("Available but not Ready")
                    return Response({'detail': 'Your Material Is Not Ready Yet please come back later.'}, status=status.HTTP_409_CONFLICT)
                else:
                    agent.ready = False
                    agent.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No agent response exists for this user."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred while processing your request: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#SUPER AGENT 1



from base.models import Asisstant

# @method_decorator(ratelimit(key='ip', rate='4/m', block=True), name='dispatch')
# class AskAgentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             try:
#                 session_id, query, question, request, token = task_queue.get()
#                 self.process_task(session_id, query, question, request, token)
#             except ValueError as e:
#                 print(f"Error unpacking values from queue: {e}")
#             except Exception as e:
#                 print(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, session_id, query, question, request, token):
#         user = request.user
#         session = get_object_or_404(InterviewSession, id=session_id)

#         # Fetch or create the most recent Assistant interaction for this session
#         agent, created = Asisstant.objects.get_or_create(session=session)

#         # Check if 20 minutes have passed since the last interaction or if the question has changed
#         time_now = timezone.now()
#         twenty_minutes_ago = time_now - timedelta(minutes=20)
#         is_new_session = created or agent.last_interaction is None or agent.last_interaction < twenty_minutes_ago
#         is_new_question = agent.question != question

#         if is_new_session or is_new_question:
#             # Reset interaction and update question
#             agent.question = question
#             agent.last_interaction = time_now

#             # AI prompt with full context
#             prompt = (
#                 f"Question: {question}\n"
#                 f"User's Query: {query}\n"
#                 "Please answer my query for the question in less than 100 words. "
#                 "You are here to clarify the question for me if I need any clarification. "
#                 "Avoid unnecessary conversations and respond with 'Sorry, can't help with that' if the query is irrelevant to the question. "
#                 "Do not give the answer to the question directly; your task is to clarify any issues I may have. "
#                 "If my query asks for a direct answer, reply with 'I can't help you with that'."
#                 "Through out this conversation you are to reply with 50 words or less"
#             )
#         else:
#             # Continue the conversation with just the user's query
#             prompt = f"InitialQuestion: {question}\nMy question: {query}"

#         # Generate response using genai
#         try:
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response = model.generate_content(prompt)
#             if not hasattr(response, '_result'):
#                 raise ValueError("Invalid response structure from AI model")
#             content = response._result.candidates[0].content.parts[0].text.strip()

#             # Additional prompt to check if the response is directly answering the question
#             check_prompt = (
#                 f"Question: {question}\n"
#                 f"Response: {content}\n"
#                 "Does the response directly answer the question? Respond with 'Yes' or 'No'."
#             )
#             check_response = model.generate_content(check_prompt)
#             if not hasattr(check_response, '_result'):
#                 raise ValueError("Invalid check response structure from AI model")
#             check_content = check_response._result.candidates[0].content.parts[0].text.strip()

#             # If the AI confirms it's directly answering the question, modify the response
#             if "yes" in check_content.lower():
#                 content = "I don't know"

#             # Check if the response exceeds 50 words
#             word_count = len(content.split())
#             if word_count > 50:
#                 # Summarize the response to be less than 50 words
#                 summarize_prompt = (
#                     f"Response: {content}\n"
#                     "Summarize the above response in less than 50 words."
#                 )
#                 summary_response = model.generate_content(summarize_prompt)
#                 if not hasattr(summary_response, '_result'):
#                     raise ValueError("Invalid summary response structure from AI model")
#                 content = summary_response._result.candidates[0].content.parts[0].text.strip()
#         except Exception as e:
#             print(f"Error generating AI response: {e}")
#             content = "An error occurred while generating a response. Please try again later."

#         # Save the response to the Assistant model and update the last interaction time
#         agent.response = content
#         agent.ready = True
#         agent.last_interaction = time_now
#         agent.save()

#         # Deduct credits from the user
#         user.credits -= 20
#         user.save()

#     def post(self, request, session_id):
#         user = request.user

#         if user.credits <= 20:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error: You are out of credits. Upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         query = request.data.get('query')
#         question = request.data.get('question')

#         if not query or not question:
#             return Response({'detail': 'Query and question are required.'}, status=status.HTTP_400_BAD_REQUEST)

#         # Generate a token for the task
#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         # Put the task in the queue for asynchronous processing
#         task_queue.put((session_id, query, question, request, token))

#         return response





# @method_decorator(ratelimit(key='ip', rate='4/m', block=True), name='dispatch')
# class AskAgentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()
#         genai.configure(api_key=settings.GOOGLE_API_KEY)

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             session_id, query, question, request, token = task_queue.get()
#             try:
#                 self.process_task(session_id, query, question, request, token)
#             except Exception as e:
#                 print(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, session_id, query, question, request, token):
#         user = request.user
#         session = get_object_or_404(InterviewSession, id=session_id)

#         # Fetch or create the most recent Assistant interaction for this session
#         agent, created = Asisstant.objects.get_or_create(session=session)

#         # Check if 20 minutes have passed since the last interaction or if the question has changed
#         time_now = timezone.now()
#         twenty_minutes_ago = time_now - timedelta(minutes=20)
#         is_new_session = created or agent.last_interaction is None or agent.last_interaction < twenty_minutes_ago
#         is_new_question = agent.question != question

#         if is_new_session or is_new_question:
#             # Reset interaction and update question
#             agent.question = question
#             agent.last_interaction = time_now

#             # AI prompt with full context
#             prompt = (
#                 f"Question: {question}\n"
#                 f"User's Query: {query}\n"
#                 "Please answer my query for the question in less than 100 words. "
#                 "You are here to clarify the question for me if I need any clarification. "
#                 "Avoid unnecessary conversations and respond with 'Sorry, can't help with that' if the query is irrelevant to the question. "
#                 "Do not give the answer to the question directly; your task is to clarify any issues I may have. "
#                 "If my query asks for a direct answer, reply with 'I can't help you with that'."
#                 "Through out this conversation you are to reply with 50 words or less"
#             )
#         else:
#             # Continue the conversation with just the user's query
#             prompt = f"InitialQuestion: {question}\nMy question: {query}"

#         # Generate response using genai
#         try:
#             model = genai.GenerativeModel('gemini-1.0-pro-latest')
#             response = model.generate_content(prompt)
#             if not hasattr(response, '_result'):
#                 raise ValueError("Invalid response structure from AI model")
#             content = response._result.candidates[0].content.parts[0].text.strip()

#             # Additional prompt to check if the response is directly answering the question
#             check_prompt = (
#                 f"Question: {question}\n"
#                 f"Response: {content}\n"
#                 "Does the response directly answer the question? Respond with 'Yes' or 'No'."
#             )
#             check_response = model.generate_content(check_prompt)
#             if not hasattr(check_response, '_result'):
#                 raise ValueError("Invalid check response structure from AI model")
#             check_content = check_response._result.candidates[0].content.parts[0].text.strip()

#             # If the AI confirms it's directly answering the question, modify the response
#             if "yes" in check_content.lower():
#                 content = "I don't know"

#             # Check if the response exceeds 50 words
#             word_count = len(content.split())
#             if word_count > 50:
#                 # Summarize the response to be less than 50 words
#                 summarize_prompt = (
#                     f"Response: {content}\n"
#                     "Summarize the above response in less than 50 words."
#                 )
#                 summary_response = model.generate_content(summarize_prompt)
#                 if not hasattr(summary_response, '_result'):
#                     raise ValueError("Invalid summary response structure from AI model")
#                 content = summary_response._result.candidates[0].content.parts[0].text.strip()
#         except Exception as e:
#             print(f"Error generating AI response: {e}")
#             content = "An error occurred while generating a response. Please try again later."

#         # Save the response to the Assistant model and update the last interaction time
#         agent.response = content
#         agent.ready = True
#         agent.last_interaction = time_now
#         agent.save()

#         # Deduct credits from the user
#         user.credits -= 20
#         user.save()

#     def post(self, request, session_id):
#         user = request.user

#         if user.credits <= 20:
#             notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
#             Notification.objects.create(user=request.user, message=notification_message)

#             return Response({'detail': 'Error: You are out of credits. Upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         query = request.data.get('query')
#         question = request.data.get('question')

#         if not query or not question:
#             return Response({'detail': 'Query and question are required.'}, status=status.HTTP_400_BAD_REQUEST)

#         # Generate a token for the task
#         token = self.generate_token()
#         response_data = {"token": str(token)}
#         response = Response(response_data, status=status.HTTP_200_OK)

#         # Put the task in the queue for asynchronous processing
#         task_queue.put((session_id, query, question, request, token))

#         return response

@method_decorator(ratelimit(key='ip', rate='4/m', block=True), name='dispatch')
class AskAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def post(self, request, session_id):
        user = request.user

        if user.credits <= 20:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error: You are out of credits. Upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        query = request.data.get('query')
        question = request.data.get('question')

        if not query or not question:
            return Response({'detail': 'Query and question are required.'}, status=status.HTTP_400_BAD_REQUEST)

        session = get_object_or_404(InterviewSession, id=session_id)

        try:
            # Fetch or create the most recent Assistant interaction for this session
            agent, created = Asisstant.objects.get_or_create(session=session)

            # Check if 20 minutes have passed since the last interaction or if the question has changed
            time_now = timezone.now()
            twenty_minutes_ago = time_now - timedelta(minutes=20)
            is_new_session = created or agent.last_interaction is None or agent.last_interaction < twenty_minutes_ago
            is_new_question = agent.question != question

            if is_new_session or is_new_question:
                # Reset interaction and update question
                agent.question = question
                agent.last_interaction = time_now

                # AI prompt with full context
                prompt = (
                    f"Question: {question}\n"
                    f"User's Query: {query}\n"
                    "Please answer my query for the question in less than 100 words. "
                    "You are here to clarify the question for me if I need any clarification. "
                    "Avoid unnecessary conversations and respond with 'Sorry, can't help with that' if the query is irrelevant to the question. "
                    "Do not give the answer to the question directly; your task is to clarify any issues I may have. "
                    "If my query asks for a direct answer, reply with 'I can't help you with that'."
                    "Through out this conversation you are to reply with 50 words or less"
                )
            else:
                # Continue the conversation with just the user's query
                prompt = f"InitialQuestion: {question}\nMy question: {query}"

            # Generate response using genai
            try:
                model = genai.GenerativeModel('gemini-1.0-pro-latest')
                response = model.generate_content(prompt)
                if not hasattr(response, '_result'):
                    raise ValueError("Invalid response structure from AI model")
                content = response._result.candidates[0].content.parts[0].text.strip()

                # Additional prompt to check if the response is directly answering the question
                check_prompt = (
                    f"Question: {question}\n"
                    f"Response: {content}\n"
                    "Does the response directly answer the question? Respond with 'Yes' or 'No'."
                )
                check_response = model.generate_content(check_prompt)
                if not hasattr(check_response, '_result'):
                    raise ValueError("Invalid check response structure from AI model")
                check_content = check_response._result.candidates[0].content.parts[0].text.strip()

                # If the AI confirms it's directly answering the question, modify the response
                if "yes" in check_content.lower():
                    content = "I don't know"

                # Check if the response exceeds 50 words
                word_count = len(content.split())
                if word_count > 50:
                    # Summarize the response to be less than 50 words
                    summarize_prompt = (
                        f"Response: {content}\n"
                        "Summarize the above response in less than 50 words."
                    )
                    summary_response = model.generate_content(summarize_prompt)
                    if not hasattr(summary_response, '_result'):
                        raise ValueError("Invalid summary response structure from AI model")
                    content = summary_response._result.candidates[0].content.parts[0].text.strip()
            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                content = "An error occurred while generating a response. Please try again later."

            # Save the response to the Assistant model and update the last interaction time
            agent.response = content
            agent.ready = True
            agent.last_interaction = time_now
            agent.save()

            # Deduct credits from the user
            user.credits -= 20
            user.save()

            return Response({'detail': 'Query processed successfully.', 'response': content}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return Response({'detail': 'Error processing the query.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)













import requests
# #SUPER AGENT 2
# class CheckSessionExpiredView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, session_id):
#         session = get_object_or_404(InterviewSession, id=session_id)

#         # Check if the session is expired
#         current_time = timezone.now()
#         one_hour_after_start = session.start_time + timezone.timedelta(hours=1)

#         if current_time > one_hour_after_start:


#             # Trigger the external URL
#             material_id = session_id
#             marking_view = InterviewRoomMarkingView.as_view()
#             response = marking_view(request._request, material_id=session_id)  # Pass the internal request object and session ID

#             if response.status_code != 200:
#                 return Response({'detail': 'Failed to mark the interview room.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#             session.expired = True
#             session.save()
#             return Response({'detail': 'Session marked as expired and marking view triggered.'}, status=status.HTTP_200_OK)

        
#         return Response({'detail': 'Session is not expired yet.'}, status=status.HTTP_200_OK)


class CheckSessionExpiredView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get all interviews belonging to the requesting user
        interviews = Interview.objects.filter(user=request.user)

        # Get all sessions belonging to the user's interviews that are not marked as expired
        sessions = InterviewSession.objects.filter(interview__in=interviews, expired=False)

        current_time = timezone.now()
        updated_sessions = []

        for session in sessions:
            one_hour_after_start = session.start_time + timezone.timedelta(hours=1)

            if current_time > one_hour_after_start:
                # Trigger the marking view for each expired session
                marking_view = InterviewRoomMarkingView.as_view()
                response = marking_view(request._request, material_id=session.id)

                if response.status_code == 200:
                    session.expired = True
                    session.save()
                    user_usessions = request.user.usessions
                    user = request.user
                    user.usessions = user_usessions - 1
                    user.save()
                    updated_sessions.append(session.id)
                else:
                    return Response({'detail': f'Failed to mark the interview room for session {session.id}.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if updated_sessions:
            return Response({'detail': f'Sessions {updated_sessions} marked as expired and marking view triggered.'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'No sessions were marked as expired.'}, status=status.HTTP_200_OK)


from base.models import Code
from base.serializers import CodeSerializer

# @method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='dispatch')
# class RunCodeView(APIView):
#     permission_classes = [IsAuthenticated]

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.daemon = True
#         self.worker_thread.start()

#     def generate_token(self):
#         return uuid.uuid4()

#     def worker(self):
#         while True:
#             try:
#                 user, script, language, version_index, request_token = task_queue.get()
#                 self.process_task(user, script, language, version_index, request_token)
#             except ValueError as e:
#                 logger.error(f"ValueError: {e}")
#             except Exception as e:
#                 logger.error(f"Error processing task: {e}")
#             finally:
#                 task_queue.task_done()

#     def process_task(self, user, script, language, version_index, request_token):
#         try:
#             payload = {
#                 'script': script,
#                 'language': language,
#                 'clientId': settings.JDOODLE_CLIENT_ID,
#                 'clientSecret': settings.JDOODLE_CLIENT_SECRET
#             }

#             if version_index is not None:
#                 payload['versionIndex'] = version_index

#             response = requests.post('https://api.jdoodle.com/v1/execute', json=payload)

#             if response.status_code != 200:
#                 logger.error(f"Error from JDoodle API: {response.text}")
#                 return

#             # Ensure the user has only one Code object
#             Code.objects.filter(user=user).delete()

#             # Save the new Code object
#             code = Code.objects.create(
#                 user=user,
#                 script=script,
#                 response=response.text
#             )

#             code.ready = True
#             code.save()

#             # Deduct credits from the user
#             user.credits -= 5
#             user.save()

#             logger.info(f"Task completed successfully for token: {request_token}")
#         except Exception as e:
#             logger.error(f"An error occurred while processing the request: {e}")

#     def post(self, request, *args, **kwargs):
#         user = request.user

#         if user.credits <= 5:
#             return Response({'detail': 'Error: You are out of credits. Upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

#         data = request.data
#         script = data.get('script')
#         language = data.get('language')
#         version_index = data.get('versionIndex')

#         if not script or not language:
#             return Response({"error": "Invalid request data"}, status=status.HTTP_400_BAD_REQUEST)

#         # Generate a token for this task
#         request_token = self.generate_token()

#         # Queue the task
#         task_queue.put((user, script, language, version_index, request_token))

#         # Return the token immediately
#         return Response({"token": str(request_token)}, status=status.HTTP_200_OK)
@method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='dispatch')
class RunCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.credits <= 5:
            notification_message = f'It seems you are out of credits please upgrade your account or contact support :)'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response({'detail': 'Error: You are out of credits. Upgrade your account or contact support.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        script = data.get('script')
        language = data.get('language')
        version_index = data.get('versionIndex')

        if not script or not language:
            return Response({"error": "Invalid request data"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = {
                'script': script,
                'language': language,
                'clientId': settings.JDOODLE_CLIENT_ID,
                'clientSecret': settings.JDOODLE_CLIENT_SECRET
            }

            if version_index is not None:
                payload['versionIndex'] = version_index

            response = requests.post('https://api.jdoodle.com/v1/execute', json=payload)

            if response.status_code != 200:
                logger.error(f"Error from JDoodle API: {response.text}")
                return Response({'detail': 'Error from JDoodle API'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Ensure the user has only one Code object
            Code.objects.filter(user=user).delete()

            # Save the new Code object
            code = Code.objects.create(
                user=user,
                script=script,
                response=response.text
            )

            code.ready = True
            code.save()

            # Deduct credits from the user
            user.credits -= 5
            user.save()

            logger.info(f"Task completed successfully for user: {user.username}")

            return Response({'detail': 'Code executed successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"An error occurred while processing the request: {e}")
            return Response({'detail': 'An error occurred while processing the request.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            # Check if the user has a Code object
            code = Code.objects.filter(user=request.user).first()

            if code:
                # Serialize and return the Code object
                serializer = CodeSerializer(code)
                if code.ready == False:
                    return Response({'detail': 'Your Material Is Not Ready Yet please come back later.'}, status=status.HTTP_409_CONFLICT)
                else: 
                    code.ready = False
                    code.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No code exists for this user."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred while processing your request: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)