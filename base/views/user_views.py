from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import generics
from ..serializers import *
from django.db import IntegrityError
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from ..models import CustomUser  as Userr
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
from base.utils import send_normal_email

# Create your views here.



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
from base.core_apis.cognito_utils import exchange_code_for_tokens, get_user_info



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














# jennie/base/views.py
import os

class RegisterUser(APIView):
    def post(self, request):
        data = request.data

        # Password validation
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response({'detail': list(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        try:
            user = Userr.objects.create_user(
                first_name=data['name'],
                username=data['email'],
                email=data['email'],
                password=data['password'],
            )

            # Load email template
            template_path = os.path.join(settings.BASE_DIR, 'email_templates', 'Welcome.html')
            with open(template_path, 'r') as template_file:
                html_content = template_file.read()

            # # Send email
            # email_data = {
            #     'email_subject': 'Welcome to Jennie',
            #     'to_email': user.email,
            #     'email_body': html_content,
            # }
            # send_normal_email(email_data)


            email_tings = {
                'email_subject': 'Welcome to Jennie',
                'to_email': user.email,
                'email_body': "Fuck you", 
            }
            # send_normal_email(email_tings)


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
        user.isPrivate = data.get('isPrivate', user.bio)




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


