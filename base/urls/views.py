from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import generics
from base.serializers import *
from django.db import IntegrityError
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from base.models import CustomUser  as Userr
from ast import Expression
from multiprocessing import context
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from base.core_apis.cognito_utils import exchange_code_for_tokens, get_user_info


# Create your views here.



class CognitoAuthView(APIView):
    def post(self, request):
        # Step 1: Get the auth code from the request
        auth_code = request.data.get('auth_code')

        # Step 2: Exchange auth code for tokens
        token_response = exchange_code_for_tokens(auth_code)
        if not token_response:
            return Response({'detail': 'Invalid authorization code'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 3: Get user info using the access token
        access_token = token_response.get('access_token')
        if not access_token:
            return Response({'detail': 'Access token missing'}, status=status.HTTP_400_BAD_REQUEST)

        user_info = get_user_info(access_token)
        if not user_info:
            return Response({'detail': 'Failed to fetch user info'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract email from Cognito user info
        email = user_info.get('email')

        # Step 4: Check if the user exists
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Create new user if not exists
            try:
                user = CustomUser.objects.create(
                    email=email,
                    username=email,
                    first_name=user_info.get('given_name', ''),
                    last_name=user_info.get('family_name', ''),
                    bio=user_info.get('bio', ''),
                    isPrivate=user_info.get('isPrivate', False),
                    auth_provider='cognito',
                )
            except IntegrityError:
                return Response({'detail': 'Error creating user'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 5: Generate tokens for the user
        refresh = RefreshToken.for_user(user)
        user_serializer = UserSerializer(user)

        # Step 6: Filter the user data and construct the response
        filtered_user_data = {
            'id': user_serializer.data['id'],
            '_id': user_serializer.data['id'],
            'username': user_serializer.data['username'],
            'email': user_serializer.data['email'],
            'name': user_serializer.data['first_name'],
            'isAdmin': user_serializer.data['is_staff'],
            'bio': user_serializer.data['bio'],
            'date_joined': user_serializer.data['date_joined'],
        }

        # Include the token field
        filtered_user_data['token'] = str(refresh.access_token)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            **filtered_user_data,
        }, status=status.HTTP_200_OK)



from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import status, views
from django.db import transaction

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class GoogleAuthView(APIView):
    def post(self, request, *args, **kwargs):
        auth_code = request.data.get("auth_code")
        if not auth_code:
            return Response(
                {"error": "Missing authentication code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print(f"Auth Code Received: {auth_code}")
        print(f"Current UTC Time: {datetime.now(timezone.utc)}")  # Log current UTC time for debugging
        print(f"Local Time: {datetime.now()}")  # Log local time for additional context

        # Initialize Google OAuth flow with events scope
        flow = Flow.from_client_config(
            settings.GOOGLE_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/calendar.events"],
        )
        flow.redirect_uri = settings.GOOGLE_CREDENTIALS["web"]["redirect_uris"][1]

        try:
            # Fetch tokens using the auth code
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            # Extract credentials data
            access_token = credentials.token
            refresh_token = credentials.refresh_token
            expiry = (
                credentials.expiry
                if isinstance(credentials.expiry, datetime)
                else datetime.now(timezone.utc) + timedelta(seconds=credentials.expiry - datetime.now().timestamp())
            )

            # Adjust the token expiry to match East African Time (UTC + 3 hours)
            expiry_eat = expiry + timedelta(hours=3)

            print(f"Access Token: {access_token}")
            print(f"Refresh Token: {refresh_token}")
            print(f"Token Expiry Time (EAT): {expiry_eat}")

            # Update the user object
            user = request.user
            with transaction.atomic():
                user.google_calendar_token = access_token
                user.google_calendar_refresh_token = refresh_token
                user.google_calendar_token_expiry = expiry_eat
                user.save()
                print("User tokens successfully saved.")

            return Response(
                {
                    "message": "Google authentication successful",
                    "tokens": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as ve:
            print(f"Value error during token exchange: {ve}")
            return Response(
                {"error": "Invalid authentication code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
       def validate(self, attrs: dict[str, any]) -> dict[str, str]:
        data = super().validate(attrs)
        serializer = UserSerializerWithToken(self.user).data

        for k, v in serializer.items():
            data[k] = v



        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer







from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404


from rest_framework.response import Response
from django.db.models import Q






from django.db.models import Case, When, Value, IntegerField

from django.db.models import Q, F
from rest_framework.pagination import PageNumberPagination




from rest_framework.parsers import MultiPartParser, FormParser

@permission_classes([IsAdminUser])
class UpdateUser(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, pk):
        try:
            user = Userr.objects.get(id=pk)
            data = request.data

            # Update user profile details
            user.first_name = data.get('name', user.first_name)
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            user.is_staff = data.get('isAdmin', user.is_staff)


            user.save()

            serializer = UserSerializer(user, many=False)

            # Return updated user data
            return Response(serializer.data)

        except Userr.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)
        except Exception as e:
            return Response({'detail': f'Error updating user profile: {str(e)}'}, status=500)

from django.contrib.auth.validators import UnicodeUsernameValidator
import os

class RegisterUser(APIView):

    def post(self, request):
        data = request.data

        # Check password length
        if len(data['password']) < 8:
            content = {'detail': 'Password must be at least 8 characters long.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # Check password for username and email
        username_validator = UnicodeUsernameValidator()
        if username_validator(data['password']):
            content = {'detail': 'Password cannot contain username or email.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # Check for minimum number of upper and lowercase characters
        uppercase_count = sum(1 for c in data['password'] if c.isupper())
        lowercase_count = sum(1 for c in data['password'] if c.islower())
        if uppercase_count < 1 or lowercase_count < 1:
            content = {'detail': 'Password must contain at least one uppercase and lowercase character.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # Check for minimum number of digits and special characters
        digit_count = sum(1 for c in data['password'] if c.isdigit())
        special_count = sum(1 for c in data['password'] if not c.isalnum())
        if digit_count < 1 or special_count < 1:
            content = {'detail': 'Password must contain at least one digit and one special character.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        try:
            user = Userr.objects.create_user(
                first_name=data['name'],
                username=data['email'],
                email=data['email'],
                password=data['password'],
            )



            # Load email template
            template_path = os.path.join(settings.BASE_DIR, 'base/email_templates', 'Welcome.html')
            with open(template_path, 'r', encoding='utf-8') as template_file:
                html_content = template_file.read()


            # Send email
            email_data = {
                'email_subject': 'Welcome to Jennie',
                'to_email': user.email,
                'email_body': html_content,
            }
            send_normal_email(email_data)


            # email_body = f"Hi {user.first_name}, Welcome To Gallery The Best Social App ! Remember To Leave A Review On Your Experience."
            # email_subject = "WELCOME HOME"
            # to_email = user.email
            # data = {
            #     'email_body': email_body,
            #     'email_subject': email_subject,
            #     'to_email': to_email
            # }
            # send_normal_email(data)
        except IntegrityError:
            message = {'detail': 'User with this email already exists.'}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(user, many=False)
        return Response(serializer.data)



@permission_classes([IsAuthenticated])
class GetUserProfile(APIView):

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user, many=False)


        return Response(serializer.data)

@permission_classes([IsAuthenticated])
class UpdateUserProfile(APIView):

    def put(self, request):
        user = request.user
        serializer = UserSerializerWithToken(user, many=False)
        data = request.data

        # Update password if provided
        if 'password' in data and data['password'] != '':
            # Add password strength checks here
            if len(data['password']) < 8:
                content = {'detail': 'Password must be at least 8 characters long.'}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)

            uppercase_count = sum(1 for c in data['password'] if c.isupper())
            lowercase_count = sum(1 for c in data['password'] if c.islower())
            if uppercase_count < 1 or lowercase_count < 1:
                content = {'detail': 'Password must contain at least one uppercase and lowercase character.'}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)

            digit_count = sum(1 for c in data['password'] if c.isdigit())
            special_count = sum(1 for c in data['password'] if not c.isalnum())
            if digit_count < 1 or special_count < 1:
                content = {'detail': 'Password must contain at least one digit and one special character.'}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)

            user.password = make_password(data['password'])

        # Update user profile details
        user.first_name = data.get('name', user.first_name)
        user.username = data.get('email', user.username)
        user.email = data.get('email', user.email)
        user.bio = data.get('bio', user.bio)
        user.isPrivate = data.get('isPrivate', user.isPrivate)  # Corrected this line

        # Save updated user profile
        user.save()

        # Return updated user data
        return Response(serializer.data)


@permission_classes([IsAuthenticated])
class deleteAccount(APIView):
    def delete(self, request):
        # Use request.user to get the authenticated user
        user_for_deletion = request.user



        # Delete the user
        user_for_deletion.delete()

        return Response("The user was deleted successfully")





class PasswordResetRequestView(APIView):
    serializer_class=PasswordResetRequestSerializer

    def post(self, request):
        serializer=self.serializer_class(data=request.data, context={'request':request})
        serializer.is_valid(raise_exception=True)
        return Response({'message':'we have sent you a link to reset your password'}, status=status.HTTP_200_OK)
        # return Response({'message':'user with that email does not exist'}, status=status.HTTP_400_BAD_REQUEST)




class PasswordResetConfirm(APIView):

    def get(self, request, uidb64, token):
        try:
            user_id=smart_str(urlsafe_base64_decode(uidb64))
            user=Userr.objects.get(id=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response({'message':'token is invalid or has expired'}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'success':True, 'message':'credentials is valid', 'uidb64':uidb64, 'token':token}, status=status.HTTP_200_OK)

        except DjangoUnicodeDecodeError as identifier:
            return Response({'message':'token is invalid or has expired'}, status=status.HTTP_401_UNAUTHORIZED)

class SetNewPasswordView(GenericAPIView):
    serializer_class=SetNewPasswordSerializer

    def patch(self, request):
        serializer=self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({'success':True, 'message':"password reset is succesful"}, status=status.HTTP_200_OK)




from django.shortcuts import get_object_or_404





from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated


