import requests
from date_data import june_data, july_data  # Importing the datetime data
from minterview_tests import run_minterview_tests
import time

def create_interview(url, token, job_id, interview_datetime):
    headers = {'Authorization': f'Bearer {token}'}
    data = {
        'job': job_id,
        'interview_datetime': interview_datetime,
        'passed': False
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def view_interview(base_url, token, interview_id):
    headers = {'Authorization': f'Bearer {token}'}
    view_interview_url = f"{base_url}/api/v1/interviews/{interview_id}/"
    response = requests.get(view_interview_url, headers=headers)
    return response

def update_interview(base_url, token, interview_id, new_interview_datetime):
    headers = {'Authorization': f'Bearer {token}'}
    update_interview_url = f"{base_url}/api/v1/interviews/{interview_id}/update/"
    data = {
        'interview_datetime': new_interview_datetime
    }
    response = requests.put(update_interview_url, headers=headers, json=data)
    return response

def delete_interview(base_url, token, interview_id):
    headers = {'Authorization': f'Bearer {token}'}
    delete_interview_url = f"{base_url}/api/v1/interviews/{interview_id}/delete/"
    response = requests.delete(delete_interview_url, headers=headers)
    return response

def list_user_interviews(base_url, token):
    headers = {'Authorization': f'Bearer {token}'}
    list_interviews_url = f"{base_url}/api/v1/interviews/"
    response = requests.get(list_interviews_url, headers=headers)
    return response

def run_interview_tests(base_url, token, job_ids):
    create_interview_url = f"{base_url}/api/v1/interviews/create/"
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for i, job_id in enumerate(job_ids):
        interview_datetime = june_data[i % len(june_data)]  # Pick a datetime from june_data
        # Create an interview
        interview_response = create_interview(create_interview_url, token, job_id, interview_datetime)
        total_tests += 1
        if interview_response.status_code == 201:
            print(f"Interview created successfully for job ID {job_id} with datetime {interview_datetime}.")
            passed_tests += 1
            interview_id = interview_response.json().get('id')
            # time.sleep(10000)
            if interview_id:
                # View the created interview
                view_response = view_interview(base_url, token, interview_id)
                total_tests += 1
                if view_response.status_code == 200:
                    print(f"Interview viewed successfully for interview ID {interview_id}.")
                    passed_tests += 1

                    # Update the interview with a new datetime
                    new_interview_datetime = july_data[(i + 1) % len(july_data)]
                    update_response = update_interview(base_url, token, interview_id, new_interview_datetime)
                    total_tests += 1
                    if update_response.status_code == 200:
                        print(f"Interview updated successfully for interview ID {interview_id} with new datetime {new_interview_datetime}.")
                        passed_tests += 1

                        # View the updated interview
                        view_updated_response = view_interview(base_url, token, interview_id)
                        total_tests += 1
                        if view_updated_response.status_code == 200:
                            print(f"Updated interview viewed successfully for interview ID {interview_id}.")
                            passed_tests += 1


                            # Run interview tests after viewing the job
                            minterview_tests_passed, minterview_tests_total, minterview_failed_tests = run_minterview_tests(base_url, token, [interview_id])
                            passed_tests += minterview_tests_passed
                            total_tests += minterview_tests_total
                            failed_tests.extend(minterview_failed_tests)

                            # List all user's interviews before deletion
                            list_response_before = list_user_interviews(base_url, token)
                            total_tests += 1
                            if list_response_before.status_code == 200:
                                print("User's interviews listed successfully before deletion.")
                                passed_tests += 1

                                # Delete the interview
                                delete_response = delete_interview(base_url, token, interview_id)
                                total_tests += 1
                                if delete_response.status_code == 204:
                                    print(f"Interview deleted successfully for interview ID {interview_id}.")
                                    passed_tests += 1

                                    # List all user's interviews after deletion
                                    list_response_after = list_user_interviews(base_url, token)
                                    total_tests += 1
                                    if list_response_after.status_code == 200:
                                        print("User's interviews listed successfully after deletion.")
                                        passed_tests += 1
                                        if any(interview['id'] == interview_id for interview in list_response_after.json()):
                                            print(f"Error: Deleted interview ID {interview_id} still present in user's interviews.")
                                            failed_tests.append(f"Deleted interview ID {interview_id} still present in user's interviews")
                                        else:
                                            print(f"Interview ID {interview_id} correctly deleted from user's interviews.")
                                    else:
                                        print(f"Error listing user's interviews after deletion: {list_response_after.text}")
                                        failed_tests.append("List user's interviews after deletion")
                                else:
                                    print(f"Error deleting interview ID {interview_id}: {delete_response.text}")
                                    failed_tests.append(f"Delete interview ID {interview_id}")
                            else:
                                print(f"Error listing user's interviews before deletion: {list_response_before.text}")
                                failed_tests.append("List user's interviews before deletion")
                        else:
                            print(f"Error viewing updated interview ID {interview_id}: {view_updated_response.text}")
                            failed_tests.append(f"View updated interview ID {interview_id}")
                    else:
                        print(f"Error updating interview ID {interview_id}: {update_response.text}")
                        failed_tests.append(f"Update interview ID {interview_id}")
                else:
                    print(f"Error viewing interview ID {interview_id}: {view_response.text}")
                    failed_tests.append(f"View interview ID {interview_id}")
            else:
                print("Interview ID not found in the creation response.")
                failed_tests.append(f"Fetch interview ID for job ID {job_id}")
        else:
            print(f"Error creating interview for job ID {job_id}: {interview_response.text}")
            failed_tests.append(f"Create interview for job ID {job_id}")

    return passed_tests, total_tests, failed_tests
