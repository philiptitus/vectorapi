from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from base.models import InterviewSession, InterviewBlock, InterviewCodingQuestion
import time
import re
import google.generativeai as genai  # Import the generative AI module
from base.core_apis.codestral_ai import call_chat_endpoint  # Import the codestral AI function
from base.core_apis.fetch_language import extract_language_from_answer  # Import the codestral AI function
from base.core_apis.extract_score import extract_first_number



@shared_task
def mark_interview_room(material_id):
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    
    interview_session = InterviewSession.objects.get(id=material_id)
    blocks = InterviewBlock.objects.filter(session=interview_session)
    codes = InterviewCodingQuestion.objects.filter(session=interview_session)

    if not blocks.exists():
        return {'detail': 'No blocks found for this preparation material.'}

    scores = []
    for block in blocks:
        if not block.my_answer:
            block.my_answer = "I don't know"
            block.save()
        if not (block.question and block.answer):
            return {'detail': f'Block ID {block.id} is missing required fields.'}

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
            score = float(score_text.split(':')[-1].strip())
            block.score = score
            block.save()
        except Exception as e:
            return {'detail': f'Error generating similarity score: {e}'}

        scores.append(f"Question {block.id}: {score_text}")
        time.sleep(6)

    if not codes.exists():
        return {'detail': 'No coding questions found for this preparation material.'}

    code_scores = []
    for code in codes:
        if not code.my_answer:
            code.my_answer = "I don't know"
            code.save()
        if not (code.question and code.answer):
            return {'detail': f'Code ID {code.id} is missing required fields.'}

        code_prompt = (
            f"Check the following coding question:\n\n"
            f"My Answer: {code.my_answer}\n"
            f"Answer: {code.answer}\n\n"
            "Assign a score from 1 to 100 based on how close 'My Answer' is to 'Answer'.\n\n"
            "Please be very very strict in marking and awarding scores. For instance, if they are very far apart, just give 0. Keep it simple:\n\n"
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
            number = extract_first_number(ai_response)
            if number:
                code_score = float(number)
                code.score = code_score
                code.save()
            else:
                raise ValueError("No numeric score found in response.")
        except Exception as e:
            return {'detail': f'Error generating coding question score: {e}'}

        code_scores.append(f"Question {code.id}: {ai_response}")
        time.sleep(5)

    block_scores = InterviewBlock.objects.filter(session=interview_session).values_list('score', flat=True)
    code_scores = InterviewCodingQuestion.objects.filter(session=interview_session).values_list('score', flat=True)

    all_scores = list(block_scores) + list(code_scores)
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0

    interview_session.score = overall_score
    interview_session.marked = True
    interview_session.save()

    return {'detail': 'Scores calculated successfully.', 'scores': scores, 'code_scores': code_scores, 'overall_score': overall_score}




from base.models import Interview, InterviewSession, InterviewBlock, InterviewCodingQuestion
import time




@shared_task
def create_interview_session_task(job_id, user_id):
    try:
        # Fetch the job and user
        job = Interview.objects.get(id=job_id, user_id=user_id)
        description = job.job.description
        title = job.job.title
        print(f"Fetched job: {title}, for user: {user_id}")

        # Create an InterviewSession instance
        interview_session = InterviewSession.objects.create(interview=job)
        print(f"Created InterviewSession: {interview_session.id}")

        # Prompt 1
        prompt1 = f"Based on this {description}, will you need to write code in the future? Answer YES or NO. Enclose your response in []."
        model = genai.GenerativeModel('gemini-1.0-pro-latest')
        response1 = model.generate_content(prompt1)
        content1 = response1._result.candidates[0].content.parts[0].text.strip()
        print(f"Prompt 1 response: {content1}")

        # Prompt 4 - Iteratively ask for questions and answers
        questions_and_answers = []
        for i in range(15):
            print(f"Starting iteration {i+1} for Prompt 4")
            prompt4 = f"Based on this {description}, provide me just one question and its answer which would be asked in the related interview. Make the question 80% more difficult than the actual ones you expect to be asked. Note the answer part should be very detailed and start with the word 'Answer' while the question should start with the word 'Question'. If the description involves an interview that deals with code don't make any question that requires you to give code snippet as an answer. Write question along with its answer."
            response4 = model.generate_content(prompt4)
            content4 = response4._result.candidates[0].content.parts[0].text.strip()
            print(f"Prompt 4 response: {content4}")

            # Parsing the response to extract question and answer
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
                print(f"Added question: {question}")
                print(f"Added answer: {answer}")

            time.sleep(5)  # Wait for 5 seconds before the next iteration
            print(f"Iteration {i+1} completed")

        # Save the extracted questions and answers
        for q, a in questions_and_answers:
            InterviewBlock.objects.create(
                session=interview_session,
                question=q,
                answer=a,
                score=0  # Assuming the score starts at 0
            )
            print(f"Saved question and answer pair to InterviewBlock: {q}, {a}")

        # Uncomment the following if you need to include Prompt 5 based on Prompt 1's response
        if content1 == "[YES]":
            questions_and_answers_coding = []
            for i in range(5):
                print(f"Starting iteration {i+1} for Prompt 5")
                prompt5 = f"Please provide me with just a single interview coding question and its answer given as a code snippet, for this description: {description}. Make it 90% harder than what you would actually expect. FOR EASY IDENTIFICATION LABEL THE QUESTION AS 'Question' and the answer as 'Answer'."
                response5 = model.generate_content(prompt5)
                content5 = response5._result.candidates[0].content.parts[0].text.strip()
                print(f"Prompt 5 response: {content5}")

                # Parsing the response to extract question and answer
                lines = content5.split('\n')
                question = ""
                answer = ""
                is_question = False
                is_answer = False

                for line in lines:
                    stripped_line = line.strip()
                    if not stripped_line:
                        continue
                    if 'Question' in stripped_line and not is_question:
                        if question and answer:
                            questions_and_answers_coding.append((question, answer))
                            question = ""
                            answer = ""
                        question = stripped_line
                        is_question = True
                        is_answer = False
                    elif 'Answer' in stripped_line and is_question:
                        answer = stripped_line
                        is_answer = True
                        is_question = False
                    elif is_question:
                        question += ' ' + stripped_line
                    elif is_answer:
                        answer += ' ' + stripped_line

                if question and answer:
                    questions_and_answers_coding.append((question, answer))
                    print(f"Added coding question: {question}")
                    print(f"Added coding answer: {answer}")

                time.sleep(5)  # Wait for 5 seconds before the next iteration
                print(f"Iteration {i+1} for Prompt 5 completed")

            # Save the coding questions and answers
            for q, a in questions_and_answers_coding:
                InterviewCodingQuestion.objects.create(
                    session=interview_session,
                    question=q,
                    answer=a,
                    language='Python'  # Assuming the language is Python; adjust as needed
                )
                print(f"Saved coding question and answer pair to InterviewCodingQuestion: {q}, {a}")

        print(f"Task completed successfully, InterviewSession ID: {interview_session.id}")
        return interview_session.id

    except Exception as e:
        # Handle exceptions and possibly log them
        print(f"Error in create_interview_session_task: {str(e)}")
        return None