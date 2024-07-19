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


@method_decorator(ratelimit(key='ip', rate='4/30m', block=True), name='dispatch')
class JobCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def post(self, request, *args, **kwargs):
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
            if job_count == 0:
                # Send email

            # Load email template
                template_path = os.path.join(settings.BASE_DIR, 'base\email_templates', 'FIRST.html')
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




class JobListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        jobs = Job.objects.filter(user=request.user)
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)




from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from django.utils.timezone import localtime, now, timedelta






from django.utils.dateparse import parse_datetime

class InterviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        job_id = data.get('job')
        job = get_object_or_404(Job, id=job_id)

        if job.user != request.user:
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        # Ensure there are no existing interviews for the job
        if Interview.objects.filter(job=job).exists():
            return Response({'detail': 'An interview has already been scheduled for this job.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check the interview datetime
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

            # Extract the date from the interview_datetime and update the job's mockup_interview_date
            interview_date = interview_datetime.date()
            job.mockup_interview_date = interview_date
            job.save()

            template_path = os.path.join(settings.BASE_DIR, 'base', 'email_templates', 'INTERVIEW.html')
            with open(template_path, 'r', encoding='utf-8') as template_file:
                html_content = template_file.read()

            # Send email
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

            # Create notification
            notification_message = f'Your interview for the job {job.title} is scheduled on {interview.interview_datetime}.'
            Notification.objects.create(user=request.user, message=notification_message)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
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

                template_path = os.path.join(settings.BASE_DIR, 'base', 'email_templates', 'Reschedule.html')
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


        template_path = os.path.join(settings.BASE_DIR, 'base', 'email_templates', 'Delete.html')
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
        interviews = Interview.objects.filter(user=request.user)
        serializer = InterviewSerializer(interviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PreparationMaterialDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        preparation_material = get_object_or_404(PreparationMaterial, id=id)
        job = preparation_material.job

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

@method_decorator(ratelimit(key='ip', rate='2/4m', block=True), name='dispatch')
class PreparationMaterialCreateView(APIView): 
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def generate_token(self):
        return uuid.uuid4()

    def worker(self):
        while True:
            job_id, token = task_queue.get()
            try:
                self.process_task(job_id, token)
            except Exception as e:
                logger.error(f"Error: {e}")
            finally:
                task_queue.task_done()

    def process_task(self, job_id, token):
        try:
            job = Job.objects.get(id=job_id)
            description = job.description
            title = job.title

            # Create a PreparationMaterial instance
            preparation_material = PreparationMaterial.objects.create(job=job, title=f"Preparation for {title}")

            # Prompt 1
            prompt1 = f"Based on this {description}, will you need to write code in the future? Answer YES or NO. Enclose your response in []."
            model = genai.GenerativeModel('gemini-1.0-pro-latest')
            response1 = model.generate_content(prompt1)
            content1 = response1._result.candidates[0].content.parts[0].text.strip()

            # Prompt 2
            prompt2 = f"Interview Preparation Tips for: {title}"
            youtube_links = get_youtube_links(prompt2)
            for yt_title, embed_url in youtube_links:
                YouTubeLink.objects.create(
                    preparation_material=preparation_material,
                    title=yt_title,
                    embed_url=embed_url
                )

            search_results = search_google(prompt2)
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

            # If Prompt 1's response is "[YES]"
            if content1 == "[YES]":
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

        except Exception as e:
            logger.error(f"Error processing task: {e}")

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(Job, id=job_id, user=request.user)

        # Generate and send token before analysis
        token = self.generate_token()
        response_data = {"token": str(token)}
        response = Response(response_data, status=status.HTTP_200_OK)

        # Add the task to the queue
        task_queue.put((job_id, token))

        return response





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
        

        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field
        block.my_answer = my_answer
        block.save()
        
        # Serialize and return the updated block
        serializer = PreparationBlockSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)





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
        

        # Get the answer from the request data
        my_answer = request.data.get('my_answer')
        if my_answer is None:
            return Response({'detail': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the answer field
        block.my_answer = my_answer
        block.save()
        
        # Serialize and return the updated block
        serializer = CodingQuestionSerializer(block)
        return Response(serializer.data, status=status.HTTP_200_OK)








import time
from django.conf import settings


@method_decorator(ratelimit(key='ip', rate='1/2m', block=True), name='dispatch')
class PreparationMaterialMarkingView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def generate_token(self):
        return uuid.uuid4()

    def worker(self):
        while True:
            material_id, token = task_queue.get()
            try:
                self.process_task(material_id, token)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
            finally:
                task_queue.task_done()

    def process_task(self, material_id, user):
        preparation_material = get_object_or_404(PreparationMaterial, id=material_id)
        blocks = PreparationBlock.objects.filter(preparation_material=preparation_material)
        codes = CodingQuestion.objects.filter(preparation_material=preparation_material)

        if not blocks.exists():
            logger.error('No blocks found for this preparation material.')
            return
        print(f"Total number of blocks found: {blocks.count()}")

        for block in blocks:
            if not (block.question and block.answer):
                if not block.my_answer:
                    block.my_answer = "i dont know!"
                    block.save()
                logger.error(f'Block ID {block.id} is missing required fields.')
                return

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

                return

            time.sleep(5)

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
                return

        for code in codes:
            print(f"Marking code: {code.id}")

            code_prompt = (
                f"Check the following coding question:\n\n"
                f"Question: {code.question}\n"
                f"My Answer: {code.my_answer}\n"
                f"Answer: {code.answer}\n\n"
                "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer' in the context of the question. Note that 'Answer' is the correct answer provided in the marking scheme and 'My Answer' is the user's response.\n\n"
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
                return

            time.sleep(5)
        print(code_scores)


        block_scores = PreparationBlock.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)
        code_scores = CodingQuestion.objects.filter(preparation_material=preparation_material).values_list('score', flat=True)


        if not codes.exists:
            all_scores = list(block_scores) 
        else:
            all_scores = list(block_scores) + list(code_scores)

        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
        print(overall_score)
        preparation_material.score = overall_score
        preparation_material.completed = True
        preparation_material.save()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        material_id = kwargs.get('material_id')
        if not material_id:
            return Response({'detail': 'Preparation Material ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        preparation_material = get_object_or_404(PreparationMaterial, id=material_id)

        token = self.generate_token()
        response_data = {"token": str(token)}
        response = Response(response_data, status=status.HTTP_200_OK)

        task_queue.put((material_id, token))

        return response






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



@method_decorator(ratelimit(key='ip', rate='2/30m', block=True), name='dispatch')
class InterviewRoomCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def generate_token(self):
        return uuid.uuid4()

    def worker(self):
        while True:
            job_id, token = task_queue.get()
            try:
                self.process_task(job_id, token)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
            finally:
                task_queue.task_done()

    def process_task(self, job_id, token):
        try:    
            
            interview = get_object_or_404(Interview, id=job_id)
            print(f"Interview found: {interview}")

            current_time = now()

            if interview.interview_datetime and current_time < interview.interview_datetime:
                logger.error('Cannot create a session earlier than the interview datetime.')
                return


            if interview.interview_datetime and current_time > interview.interview_datetime + timedelta(hours=5):
                logger.error('Cannot create a session more than 5 hours past the interview datetime.')
                return


            if InterviewSession.objects.filter(interview=interview).count() >= 2:
                logger.error('Cannot create more than 2 sessions for the same interview.')
                return


            if InterviewSession.objects.filter(interview=interview, expired=False).exists():
                logger.error('Cannot create a new session when there is an unexpired session for the same interview.')
                return


            description = interview.job.description
            interview_session = InterviewSession.objects.create(interview=interview, start_time=current_time)

            prompt1 = f"Based on this {description}, will you need to write code in the future? Answer YES or NO. Enclose your response in []."
            model = genai.GenerativeModel('gemini-1.0-pro-latest')
            response1 = model.generate_content(prompt1)
            if not hasattr(response1, '_result'):
                logger.error('Error generating AI response for prompt 1.')
                return
            content1 = response1._result.candidates[0].content.parts[0].text.strip()
            logger.info(f"AI Response for prompt 1: {content1}")
            print(f"AI Response for prompt 1: {content1}")


            questions_and_answers = []
            for i in range(15):
                prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 80% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
                response4 = model.generate_content(prompt4)
                if not hasattr(response4, '_result'):
                    logger.error(f'Error generating AI response for prompt 4, iteration {i + 1}.')
                    return
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

                time.sleep(5)


            for q, a in questions_and_answers:
                InterviewBlock.objects.create(
                    session=interview_session,
                    question=q,
                    answer=a,
                    score=0
                )


            logger.info(f"Extracted QA pairs: {questions_and_answers}")
            print(f"Extracted QA pairs: {questions_and_answers}")


            if content1 == "[YES]":
                questions_and_answers_coding = []
                for i in range(5):
                    prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 90% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer', FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer' And please number the questions!!!!!!!!!!!!!!!!!!!!!"
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

                    else:
                        print(f"Codestral AI Error: {codestral_response}")

                    time.sleep(5)

                for q, a, lang in questions_and_answers_coding:
                    InterviewCodingQuestion.objects.create(
                        session=interview_session,
                        question=q,
                        answer=a,
                        language=lang
                    )


        except Exception as e:


            print(f"Error processing task: {e}")



    @transaction.atomic
    def post(self, request, *args, **kwargs):
        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'detail': 'Job ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        token = self.generate_token()
        response_data = {"token": str(token)}
        response = Response(response_data, status=status.HTTP_200_OK)

        task_queue.put((job_id, token))

        return response



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








@method_decorator(ratelimit(key='ip', rate='2/30m', block=True), name='dispatch')
class InterviewRoomMarkingView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    def generate_token(self):
        return uuid.uuid4()

    def worker(self):
        while True:
            material_id, token = task_queue.get()
            try:
                self.process_task(material_id, token)
            except Exception as e:
                print(f"Error processing task: {e}")
            finally:
                task_queue.task_done()

    def process_task(self, material_id, token):
        interview_session = get_object_or_404(InterviewSession, id=material_id)
        blocks = InterviewBlock.objects.filter(session=interview_session)
        codes = InterviewCodingQuestion.objects.filter(session=interview_session)

        if not blocks.exists():
            print('No blocks found for this preparation material.')
            return
        print(f"Total number of blocks found: {blocks.count()}")

        for block in blocks:
            if not block.my_answer:
                block.my_answer = "I don't know"
                block.save()
            if not (block.question and block.answer):
                print(f'Block ID {block.id} is missing required fields.')
                return

        scores = []
        for block in blocks:
            print(f"Marking block: {block.id}")

            prompt = (
                f"Check the following block:\n\n"
                f"My Answer: {block.my_answer}\n"
                f"Answer: {block.answer}\n\n"
                "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
                "Please be very very strict in marking and awarding scores. For instance, if they are very far apart, just give 0. Keep it simple:\n\n"
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
                print(f"Error extracting score for block {block.id}: {e}")
                print(f"Error extracting score for block {block.id}: {e}")
                return

            time.sleep(5)

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
                return

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
                print(f"Error extracting score for coding question {code.id}: {e}")
                print(f"Error extracting score for coding question {code.id}: {e}")
                return

            time.sleep(5)
        print(code_scores)

        block_scores = InterviewBlock.objects.filter(session=interview_session).values_list('score', flat=True)
        code_scores = InterviewCodingQuestion.objects.filter(session=interview_session).values_list('score', flat=True)

        all_scores = list(block_scores) + list(code_scores)
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

        interview_session.score = overall_score
        interview_session.marked = True
        interview_session.save()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        material_id = kwargs.get('material_id')
        if not material_id:
            return Response({'detail': 'Interview Session ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        interview_session = get_object_or_404(InterviewSession, id=material_id)

        token = self.generate_token()
        response_data = {"token": str(token)}
        response = Response(response_data, status=status.HTTP_200_OK)

        task_queue.put((material_id, token))

        return response

from .tasks import mark_interview_room

#SUPER AGENT 1

@method_decorator(ratelimit(key='ip', rate='3/m', block=True), name='dispatch')
class AskAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        genai.configure(api_key=settings.GOOGLE_API_KEY)  # Configure with your Google API key

    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        query = request.data.get('query')
        question = request.data.get('question')

        if not query or not question:
            return Response({'detail': 'Query and question are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if an Agent object already exists for this session and delete it
        existing_agent = Agent.objects.filter(session=session).first()
        if existing_agent:
            existing_agent.delete()

        # AI prompt
        prompt = (
            f"Question: {question}\n"
            f"User's Query: {query}\n"
            # "THINK OF YOURSELF AS AN ASSISTANT, QUESTION REPRESENT AN INTERVIEW QUESTION WHILE USER'S QUERY REPRESENTS THE INTERVIEWEE's QUESTION REGARDING THE INTERVIEW QUESTION"
            "Please answer my query for the question in less than 100 words. "
            "Avoid unnecessary conversations and respond with 'Sorry, can't help with that' if the query is irrelevant to the question."
            "DONT GIVE THE ANSWER TO THE QUESTION YOUR WORK IS JUST TO EXPLAIN IF MY QUERY ASKS FOR A DIRECT ANSWER YOU REPLY I CANT HELP YOU WITH THAT"
            "YOUR RESPONSE SHOULD ONLY BE YOUR REPSONSE TO THE QUERY ONLY NO EXTRA WORDS!!!!!!!!!!!!!"
            "YOUR RESPONSE SHOULD ONLY BE YOUR REPSONSE TO THE QUERY ONLY NO EXTRA WORDS!!!!!!!!!!!!!"
            "YOUR RESPONSE SHOULD ONLY BE YOUR REPSONSE TO THE QUERY ONLY NO EXTRA WORDS!!!!!!!!!!!!!"



        )

        # Generate response using genai
        model = genai.GenerativeModel('gemini-1.0-pro-latest')
        response = model.generate_content(prompt)
        if not hasattr(response, '_result'):
            return Response({'detail': 'Error generating AI response.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        content = response._result.candidates[0].content.parts[0].text.strip()

        # Save the response to the Agent model
        agent = Agent.objects.create(
            session=session,
            query=query,
            question=question,
            response=content
        )

        return Response({
            'session': session_id,
            'query': query,
            'question': question,
            'response': content
        }, status=status.HTTP_201_CREATED)


import requests
#SUPER AGENT 2
class CheckSessionExpiredView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)

        # Check if the session is expired
        current_time = timezone.now()
        one_hour_after_start = session.start_time + timezone.timedelta(hours=1)

        if current_time > one_hour_after_start:


            # Trigger the external URL
            material_id = session_id
            marking_view = InterviewRoomMarkingView.as_view()
            response = marking_view(request._request, material_id=session_id)  # Pass the internal request object and session ID

            if response.status_code != 200:
                return Response({'detail': 'Failed to mark the interview room.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            session.expired = True
            session.save()
            return Response({'detail': 'Session marked as expired and marking view triggered.'}, status=status.HTTP_200_OK)

        
        return Response({'detail': 'Session is not expired yet.'}, status=status.HTTP_200_OK)
    












@method_decorator(ratelimit(key='ip', rate='3/m', block=True), name='dispatch')
class RunCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            data = request.data

            script = data.get('script')
            language = data.get('language')
            version_index = data.get('versionIndex')

            if not script or not language:
                return Response({"error": "Invalid request data"}, status=400)

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
                return Response({"error": "Error from JDoodle API", "details": response.text}, status=500)

            return Response(response.json())
        except Exception as e:
            return Response({"error": f"An error occurred while processing your request: {e}"}, status=500)
