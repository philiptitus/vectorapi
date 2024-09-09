

# Vector API for Jennie AI

This repository contains the backend API for the **Jennie AI** project, used to interact with various endpoints for testing and development purposes. You can also find the frontend code for this project in the [Jennie Frontend Repository](https://github.com/philiptitus/jennie.git).

Additionally, you can access the complete API documentation [here](https://documenter.getpostman.com/view/31401198/2sAXjDfG64).

---

## Table of Contents

1. [Technologies Used](#technologies-used)
2. [Getting Started](#getting-started)
3. [Environment Setup](#environment-setup)
4. [Running the Application](#running-the-application)
5. [Available Endpoints](#available-endpoints)
6. [Testing the API](#testing-the-api)
7. [Contributing](#contributing)
8. [License](#license)

---

## Technologies Used

The backend for **Jennie AI** is powered by Django and utilizes the following packages:

- Django 4.2.15
- Django REST Framework 3.15.2
- Simple JWT 5.3.1
- Django CORS Headers 4.4.0
- Django Ratelimit 4.1.0
- Django Redis 5.4.0
- Django Storages 1.14.4
- Celery
- Python-dotenv
- Flask 3.0.3
- Flask-CORS 4.0.1
- Gunicorn
- Psycopg2 2.9.9
- Google API Libraries (Generative AI, Authentication, etc.)

For a complete list of dependencies, refer to the `requirements.txt` file.

---

## Getting Started

### Prerequisites

Before starting, make sure you have the following installed:

- **Python** (version 3.8+)
- **PostgreSQL**
- **Redis** (optional, if using Celery)
- **Virtualenv**

### Environment Setup

1. **Clone the Repository**

   Clone the project repository from GitHub:

   ```bash
   git clone https://github.com/philiptitus/vectorapi.git
   cd vectorapi
   ```

2. **Create a Virtual Environment**

   Set up a Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**

   Install the necessary project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   Create a `.env` file in the project root directory with the following variables:

   ```bash
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

   Run database migrations:

   ```bash
   python manage.py migrate
   ```

6. **Create a Superuser**

   Set up an admin user for the Django admin interface:

   ```bash
   python manage.py createsuperuser
   ```

7. **Collect Static Files**

   Collect static assets:

   ```bash
   python manage.py collectstatic
   ```

---

## Running the Application

1. **Start the Development Server**

   Run the application locally using the Django development server:

   ```bash
   python manage.py runserver
   ```

   The app will be available at `http://localhost:8000`.

2. **Start Celery Worker (Optional)**

   If you're using Celery for background tasks, you can start the worker with:

   ```bash
   celery -A jennie worker --loglevel=info
   ```

3. **Production with Gunicorn**

   For production, you can serve the application using Gunicorn:

   ```bash
   gunicorn jennie.wsgi:application --bind 0.0.0.0:8000
   ```

---

## Available Endpoints

Here are the primary API endpoints available:

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

---

## Testing the API

You can test the API locally or on the deployed server.

- **Local Testing**: Use tools like [Postman](https://www.postman.com/) or `curl` for testing. 
- **Deployed Server**: If you prefer, you can test the deployed version of the API using the following base URL:

  ```
  https://jennie-1720624972853.ue.r.appspot.com
  ```

### Postman Testing

1. **Import Endpoints**: Create a collection in Postman and add the API endpoints with their corresponding request methods (GET, POST, PUT, DELETE).
   
2. **JWT Authentication**: For protected routes, obtain a JWT token by logging in via the `/api/users/login/` endpoint. Include the token in the `Authorization` header:

   ```
   Authorization: Bearer <your-jwt-token>
   ```

3. **Sample Request**: Example of retrieving the latest interview session:

   ```
   GET https://jennie-1720624972853.ue.r.appspot.com/api/v1/latest/
   ```

---

## Contributing

We welcome contributions! Feel free to fork this repository, make improvements, and submit pull requests. Any contributions are greatly appreciated.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

© 2024 Philip Titus

