import requests
from job_data import job_data  # Ensure this module is available with the job data
from interview_tests import run_interview_tests  # Importing the interview tests
from prep_tests import run_prep_tests
import time


def create_job(url, token, job):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(url, headers=headers, json=job)
    return response

def fetch_all_jobs(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    return response

def update_job(url, token, job):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.put(url, headers=headers, json=job)
    return response

def view_job(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    return response

def delete_job(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(url, headers=headers)
    return response


def run_job_tests(base_url, token):
    create_job_url = f"{base_url}/api/v1/jobs/create/"
    fetch_jobs_url = f"{base_url}/api/v1/jobs/"

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    job_ids = []
    for i in range(1):
        # Create a job
        job = job_data[i % len(job_data)]  # Randomly pick a job from job_data
        job_response = create_job(create_job_url, token, job)
        total_tests += 1
        if job_response.status_code == 201:
            job_id = job_response.json().get('id')
            job_ids.append(job_id)
            print(f"Job {i + 1} created successfully with ID {job_id}.")
            passed_tests += 1
        else:
            print(f"Error creating job {i + 1}: {job_response.text}")
            failed_tests.append(f"Create job {i + 1}")

    # Fetch all jobs for the user
    fetch_jobs_response = fetch_all_jobs(fetch_jobs_url, token)
    total_tests += 1
    if fetch_jobs_response.status_code == 200:
        all_jobs = fetch_jobs_response.json()
        print(f"All jobs: {all_jobs}")
        passed_tests += 1
    else:
        print(f"Error fetching jobs: {fetch_jobs_response.text}")
        failed_tests.append("Fetch all jobs")

    for job_id in job_ids:
        # Update each job
        # update_job_url = f"{base_url}/api/v1/jobs/{job_id}/update/"
        # updated_job = job_data[(job_ids.index(job_id) + 1) % len(job_data)]  # Pick another random job data
        # update_response = update_job(update_job_url, token, updated_job)
        # total_tests += 1
        # if update_response.status_code == 200:
        #     print(f"Job {job_id} updated successfully.")
        #     passed_tests += 1
        # else:
        #     print(f"Error updating job {job_id}: {update_response.text}")
        #     failed_tests.append(f"Update job {job_id}")

        # View each job
        view_job_url = f"{base_url}/api/v1/jobs/{job_id}/"
        view_response = view_job(view_job_url, token)
        total_tests += 1
        if view_response.status_code == 200:
            print(f"Job {job_id} viewed successfully: {view_response.json()}")
            passed_tests += 1

            # Run interview tests after viewing the job
            interview_tests_passed, interview_tests_total, interview_failed_tests = run_interview_tests(base_url, token, [job_id])
            passed_tests += interview_tests_passed
            total_tests += interview_tests_total
            failed_tests.extend(interview_failed_tests)

            # Run preparation material tests after viewing the job
            # prep_tests_passed, prep_tests_total, prep_failed_tests = run_prep_tests(base_url, token, [job_id])
            # passed_tests += prep_tests_passed
            # total_tests += prep_tests_total
            # failed_tests.extend(prep_failed_tests)
            # time.sleep(10000)


        else:
            print(f"Error viewing job {job_id}: {view_response.text}")
            failed_tests.append(f"View job {job_id}")

        # Delete each job
        delete_job_url = f"{base_url}/api/v1/jobs/{job_id}/delete/"
        delete_job_response = delete_job(delete_job_url, token)
        total_tests += 1
        if delete_job_response.status_code == 204:
            print(f"Job {job_id} deleted successfully.")
            passed_tests += 1
        else:
            print(f"Error deleting job {job_id}: {delete_job_response.text}")
            failed_tests.append(f"Delete job {job_id}")

    return passed_tests, total_tests, failed_tests
