"""Views for user registration and authentication."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers as drf_serializers

from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer


# Response serializers for Swagger documentation
class TokenResponseSerializer(drf_serializers.Serializer):
    refresh = drf_serializers.CharField()
    access = drf_serializers.CharField()


class AuthResponseSerializer(drf_serializers.Serializer):
    message = drf_serializers.CharField()
    user = UserSerializer()
    tokens = TokenResponseSerializer()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Register a new user",
        description="Create a new user account and receive JWT tokens",
        request=UserRegistrationSerializer,
        responses={201: AuthResponseSerializer},
        examples=[
            OpenApiExample(
                "Register Example",
                value={
                    "email": "user@example.com",
                    "name": "John Doe",
                    "password": "SecurePass123!",
                    "password_confirm": "SecurePass123!",
                    "phone": "9876543210"
                },
                request_only=True
            )
        ],
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {'refresh': str(refresh), 'access': str(refresh.access_token)}
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Login user",
        description="Authenticate with email and password to receive JWT tokens",
        request=UserLoginSerializer,
        responses={200: AuthResponseSerializer},
        examples=[
            OpenApiExample(
                "Login Example",
                value={
                    "email": "admin@irctc.com",
                    "password": "Admin@123"
                },
                request_only=True
            )
        ],
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': {'refresh': str(refresh), 'access': str(refresh.access_token)}
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    @extend_schema(
        summary="Get current user profile",
        description="Returns the profile of the authenticated user",
        responses={200: UserSerializer},
        tags=["Authentication"]
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
