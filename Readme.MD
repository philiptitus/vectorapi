
```markdown
# VECTOR API FOR JENNIE AI

This repository is the backend API for the Jennie project, which is used to test out API endpoints. The frontend for this project is available at [Jennie Frontend Repository](https://github.com/philiptitus/jennie.git).

## Table of Contents
- [Technologies Used](#technologies-used)
- [Getting Started](#getting-started)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
- [Available Endpoints](#available-endpoints)
- [Testing the API](#testing-the-api)

## Technologies Used

This project is built with Django and utilizes the following packages:

- Django==4.2.15
- djangorestframework==3.15.2
- djangorestframework-simplejwt==5.3.1
- django-cors-headers==4.4.0
- django-ratelimit==4.1.0
- django-redis==5.4.0
- django-storages==1.14.4
- Celery
- Python-dotenv
- Flask==3.0.3
- Flask-Cors==4.0.1
- Gunicorn
- Psycopg2==2.9.9
- Google API libraries (generative AI, auth, and more)

For a full list of dependencies, please refer to the `requirements.txt` file.

## Getting Started

### Prerequisites

Before setting up the project, ensure that you have the following installed:

- Python 3.8+
- PostgreSQL
- Redis (optional, if you plan to use Celery)
- Virtualenv

### Environment Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-username/jennie-backend.git
   cd jennie-backend
   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   Create a `.env` file in the project root directory with the following variables:

   ```env
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True  # Set to False in production
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432

   GOOGLE_API_KEY=your-google-api-key
   YOUTUBE_API_KEY=your-youtube-api-key
   GOOGLE_SEARCH_API_KEY=your-google-search-api-key
   GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-custom-search-engine-id

   EMAIL_HOST_USER=your-email@example.com
   EMAIL_HOST_PASSWORD=your-email-password

   # Optional Celery settings
   # CELERY_BROKER_URL=redis://localhost:6379/0
   # CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

5. **Apply Migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create a Superuser**

   ```bash
   python manage.py createsuperuser
   ```

7. **Collect Static Files**

   ```bash
   python manage.py collectstatic
   ```

## Running the Application

1. **Start the Development Server**

   ```bash
   python manage.py runserver
   ```

   The application will be available at `http://localhost:8000`.

2. **Start Celery Worker (Optional)**

   If you're using Celery for background tasks, start the worker with:

   ```bash
   celery -A jennie worker --loglevel=info
   ```

3. **Start Gunicorn for Production**

   For production, you can use Gunicorn:

   ```bash
   gunicorn jennie.wsgi:application --bind 0.0.0.0:8000
   ```

## Available Endpoints

Here are the main endpoints available in this API:

### User Endpoints (`/api/users/`)
- **Login**: `POST /api/users/login/`
- **Register**: `POST /api/users/register/`
- **Get Profile**: `GET /api/users/profile/`
- **Update Profile**: `PUT /api/users/profile/update/`
- **Delete Account**: `DELETE /api/users/delete/`
- **Password Reset Request**: `POST /api/users/password-reset/`
- **Password Reset Confirmation**: `POST /api/users/password-reset-confirm/<uidb64>/<token>/`
- **Set New Password**: `POST /api/users/set-new-password/`

### API Endpoints (`/api/v1/`)
- **Latest Interview Session**: `GET /api/v1/latest/`
- **Answer List**: `GET /api/v1/answers/`
- **Notification List**: `GET /api/v1/notifications/`
- **Check Session Expired**: `GET /api/v1/expired/`
- **Run Code**: `POST /api/v1/run/`
- **Get Code**: `GET /api/v1/code/`
- **Get Agent**: `GET /api/v1/agent/`
- **Preparation Material List**: `GET /api/v1/materials/`
- **Job List**: `GET /api/v1/jobs/`
- **Create Job**: `POST /api/v1/jobs/create/`
- **Create Interview**: `POST /api/v1/interviews/create/`
- **User Interviews**: `GET /api/v1/interviews/`

## Testing the API

You can test the API using tools like Postman or cURL.

### Postman

1. **Import Endpoints**

   You can import the API endpoints into Postman by creating a new collection and adding the above endpoints with the appropriate request methods (GET, POST, PUT, DELETE).

2. **Authorization**

   For protected endpoints, use JWT authentication. Obtain a token by logging in via the `/api/users/login/` endpoint and then set the token in the `Authorization` header:

   ```
   Authorization: Bearer <your-jwt-token>
   ```

3. **Example Request**

   To get the latest interview session:

   ```bash
   GET http://localhost:8000/api/v1/latest/
   ```

   With JWT Token in headers.

## Contributing

Feel free to fork the project and submit pull requests. Any contributions are welcome!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
```

