import requests
import time
from user_data import user_data  # Importing directly without the dot notation
from job_tests import run_job_tests  # Importing the job tests

def get_url():
    url = input("Please provide the base URL for the API (e.g., http://localhost:8000) or press 's' to use the default URL (http://127.0.0.1:8000/): ")
    return url if url != 's' else "http://127.0.0.1:8000"

def get_delay():
    delay_input = input("Please provide a delay between tests (e.g., 5m for 5 minutes, 30s for 30 seconds) or press 's' to skip delay: ")
    if delay_input == 's':
        return 0
    try:
        if delay_input.endswith('m'):
            minutes = int(delay_input[:-1])
            if minutes > 50:
                print("Maximum delay is 50 minutes. Setting delay to 50 minutes.")
                return 50 * 60
            return minutes * 60
        elif delay_input.endswith('s'):
            return int(delay_input[:-1])
        else:
            print("Invalid input. No delay will be set.")
            return 0
    except ValueError:
        print("Invalid input. No delay will be set.")
        return 0

def get_iterations():
    iterations_input = input("Please provide the number of iterations (between 1 and 30) or press 's' to use the default (1): ")
    if iterations_input == 's':
        return 1
    try:
        iterations = int(iterations_input)
        if 0 <= iterations <= 30:
            return iterations
        else:
            print("Invalid input. Setting iterations to default (1).")
            return 1
    except ValueError:
        print("Invalid input. Setting iterations to default (1).")
        return 1

def register_user(url, user):
    response = requests.post(url, data=user)
    return response

def login_user(url, username, password):
    data = {'username': username, 'password': password}
    response = requests.post(url, data=data)
    return response

def delete_user(url, token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(url, headers=headers)
    return response

def main():
    base_url = get_url()
    register_url = f"{base_url}/api/users/register/"
    login_url = f"{base_url}/api/users/login/"
    delete_user_url = f"{base_url}/api/users/delete/"
    delay = get_delay()
    iterations = get_iterations()

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for index, user in enumerate(user_data[:iterations]):  # Using the specified number of iterations
        print(f"Attempting to register user {index + 1}: {user['email']}")
        response = register_user(register_url, user)
        total_tests += 1

        if response.status_code == 200:
            print(f"User {index + 1} registered successfully.")
            passed_tests += 1
            login_response = login_user(login_url, user['email'], user['password'])
            total_tests += 1
            if login_response.status_code == 200:
                print(f"User {index + 1} logged in successfully.")
                passed_tests += 1
                token = login_response.json().get('token')
                if token:
                    # Run job tests
                    job_tests_passed, job_tests_total, job_failed_tests = run_job_tests(base_url, token)
                    passed_tests += job_tests_passed
                    total_tests += job_tests_total
                    failed_tests.extend(job_failed_tests)

                    # Delete the user
                    delete_user_response = delete_user(delete_user_url, token)
                    total_tests += 1
                    if delete_user_response.status_code == 200:
                        print(f"User {index + 1} deleted successfully.")
                        passed_tests += 1
                    else:
                        print(f"Error deleting user {index + 1}: {delete_user_response.text}")
                        failed_tests.append(f"Delete user {index + 1}")
                else:
                    print(f"No token received for user {index + 1}")
                    failed_tests.append(f"No token received for user {index + 1}")
            else:
                print(f"Error logging in user {index + 1}: {login_response.text}")
                failed_tests.append(f"Login user {index + 1}")
        else:
            print(f"Error registering user {index + 1}: {response.text}")
            failed_tests.append(f"Register user {index + 1}")
            break

        print("-" * 50)
        print("\n" * 3)

    percentage_passed = (passed_tests / total_tests) * 100
    print(f"Tests completed. {passed_tests}/{total_tests} tests passed.")
    print(f"Percentage of tests passed: {percentage_passed:.2f}%")

    if failed_tests:
        print("Failed tests:")
        for test in failed_tests:
            print(f"- {test}")

if __name__ == "__main__":
    main()
