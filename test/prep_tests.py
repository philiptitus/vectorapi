import requests
import random
import time
from vectorapi.base.answers import answers  # Importing the answers from answers.py

def create_preparation_material(url, token, job_id):
    headers = {'Authorization': f'Bearer {token}'}
    data = {'job_id': job_id}
    response = requests.post(url, headers=headers, json=data)
    return response

def view_preparation_material(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    return response

def delete_preparation_material(url, token, job_id):
    headers = {'Authorization': f'Bearer {token}'}
    data = {'job_id': job_id}
    response = requests.post(url, headers=headers, json=data)
    return response

def update_preparation_block(url, token, block_id, my_answer):
    headers = {'Authorization': f'Bearer {token}'}
    data = {'my_answer': my_answer}
    response = requests.put(url.format(block_id=block_id), headers=headers, json=data)
    return response

def update_coding_question(url, token, question_id, my_answer):
    headers = {'Authorization': f'Bearer {token}'}
    data = {'my_answer': my_answer}
    response = requests.put(url.format(id=question_id), headers=headers, json=data)
    return response

def mark_preparation_material(url, token, material_id):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(url.format(material_id=material_id), headers=headers)
    return response

def run_prep_tests(base_url, token, job_ids):
    create_material_url = f"{base_url}/api/v1/material/create/"
    view_material_url_template = f"{base_url}/api/v1/material/{{}}/"
    delete_material_url = f"{base_url}/api/v1/material/delete/"
    update_block_url_template = f"{base_url}/api/v1/p-blocks/{{block_id}}/update/"
    update_question_url_template = f"{base_url}/api/v1/code/{{id}}/update/"
    mark_material_url_template = f"{base_url}/api/v1/material/{{material_id}}/mark/"

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for job_id in job_ids:
        # Create preparation material for each job
        create_response = create_preparation_material(create_material_url, token, job_id)
        total_tests += 1
        if create_response.status_code == 201:
            print(f"Preparation material created successfully for job ID {job_id}.")
            passed_tests += 1

            # Get the created preparation material ID from the response
            preparation_material_id = create_response.json().get('id')
            blocks = create_response.json().get('blocks')
            coding_questions = create_response.json().get('coding_questions')

            # Debug print to check the response structure
            print("Response Structure:", create_response.json())

            # View the created preparation material
            if preparation_material_id:
                view_material_url = view_material_url_template.format(preparation_material_id)
                view_response = view_preparation_material(view_material_url, token)
                blocks = view_response.json().get('blocks')
                coding_questions = view_response.json().get('coding_questions')
                total_tests += 1
                if view_response.status_code == 200:
                    print(f"Preparation material viewed successfully for ID {preparation_material_id}.")
                    print(f"View Response: {view_response.json()}")
                    passed_tests += 1

                    # Update all preparation blocks
                    if blocks:
                        print(f"Blocks found: {blocks}")
                        for block in blocks:
                            block_id = block['id']
                            my_answer = random.choice(answers)
                            update_response = update_preparation_block(update_block_url_template, token, block_id, my_answer)
                            total_tests += 1
                            if update_response.status_code == 200:
                                print(f"Preparation block updated successfully for block ID {block_id}.")
                                passed_tests += 1
                            else:
                                print(f"Error updating preparation block for block ID {block_id}: {update_response.text}")
                                failed_tests.append(f"Update preparation block for block ID {block_id}")
                    else:
                        print("No blocks found in the response.")
                    
                    # Update all coding questions
                    if coding_questions:
                        print(f"Coding questions found: {coding_questions}")
                        for question in coding_questions:
                            question_id = question['id']
                            my_answer = random.choice(answers)
                            update_response = update_coding_question(update_question_url_template, token, question_id, my_answer)
                            total_tests += 1
                            if update_response.status_code == 200:
                                print(f"Coding question updated successfully for question ID {question_id}.")
                                passed_tests += 1
                            else:
                                print(f"Error updating coding question for question ID {question_id}: {update_response.text}")
                                failed_tests.append(f"Update coding question for question ID {question_id}")
                    else:
                        print("No coding questions found in the response.")

                    time.sleep(1000)  # Delay for exactly 3 minutes  

                    # Mark the preparation material
                    # mark_response = mark_preparation_material(mark_material_url_template, token, preparation_material_id)
                    # total_tests += 1
                    # if mark_response.status_code == 200:
                    #     print(f"Preparation material marked successfully for ID {preparation_material_id}.")
                    #     print(f"Mark Response: {mark_response.json()}")
                    #     passed_tests += 1
                    # else:
                    #     print(f"Error marking preparation material for ID {preparation_material_id}: {mark_response.text}")
                    #     failed_tests.append(f"Mark preparation material for ID {preparation_material_id}")
                        
                    # time.sleep(10000)

                    # Delete the preparation material
                    delete_response = delete_preparation_material(delete_material_url, token, job_id)
                    total_tests += 1
                    if delete_response.status_code == 204:
                        print(f"Preparation material deleted successfully for job ID {job_id}.")
                        passed_tests += 1
                    else:
                        print(f"Error deleting preparation material for job ID {job_id}: {delete_response.text}")
                        failed_tests.append(f"Delete preparation material for job ID {job_id}")
                else:
                    print(f"Error viewing preparation material for ID {preparation_material_id}: {view_response.text}")
                    failed_tests.append(f"View preparation material for ID {preparation_material_id}")
            else:
                print(f"No preparation material ID returned for job ID {job_id}")
                failed_tests.append(f"No preparation material ID for job ID {job_id}")
        else:
            print(f"Error creating preparation material for job ID {job_id}: {create_response.text}")
            failed_tests.append(f"Create preparation material for job ID {job_id}")

    return passed_tests, total_tests, failed_tests

# Example usage:
# base_url = "http://your-api-url.com"
# token = "your-auth-token"
# job_ids = [1, 2, 3]  # Example job IDs
# run_prep_tests(base_url, token, job_ids)
