"""
Comprehensive tests for core app - User authentication.
Tests cover: Model constraints, Serializer validation, Auth flow integration.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

User = get_user_model()


# =============================================================================
# UNIT TESTS - Models
# =============================================================================

class UserModelTests(TestCase):
    """Test User model constraints and methods."""
    
    def test_create_user_with_email(self):
        """Test creating a user with email is successful."""
        email = 'test@example.com'
        password = 'testpass123'
        user = User.objects.create_user(
            email=email,
            password=password,
            name='Test User'
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_admin)
        self.assertTrue(user.is_active)
    
    def test_email_domain_is_normalized(self):
        """Test email domain is normalized to lowercase."""
        email = 'Test@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            password='test123',
            name='Test'
        )
        # Django's normalize_email only lowercases the domain part
        self.assertEqual(user.email, 'Test@example.com')
    
    def test_email_is_unique(self):
        """Test that duplicate emails raise error."""
        User.objects.create_user(
            email='unique@example.com',
            password='test123',
            name='First User'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='unique@example.com',
                password='test123',
                name='Second User'
            )
    
    def test_create_user_without_email_raises_error(self):
        """Test creating user without email raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='test123',
                name='Test'
            )
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
            name='Admin'
        )
        
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_admin)
    
    def test_user_string_representation(self):
        """Test User __str__ returns email."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            name='Test User'
        )
        self.assertEqual(str(user), 'test@example.com')


# =============================================================================
# UNIT TESTS - Serializers
# =============================================================================

class UserSerializerTests(TestCase):
    """Test User serializers validation."""
    
    def test_registration_password_mismatch(self):
        """Test registration fails when passwords don't match."""
        from core.serializers import UserRegistrationSerializer
        
        data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'StrongPass123!',
            'password_confirm': 'DifferentPass123!'
        }
        serializer = UserRegistrationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)
    
    def test_registration_weak_password(self):
        """Test registration fails with weak password."""
        from core.serializers import UserRegistrationSerializer
        
        data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': '123',  # Too weak
            'password_confirm': '123'
        }
        serializer = UserRegistrationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_registration_duplicate_email(self):
        """Test registration fails with existing email."""
        from core.serializers import UserRegistrationSerializer
        
        # Create existing user
        User.objects.create_user(
            email='existing@example.com',
            password='test123',
            name='Existing'
        )
        
        data = {
            'email': 'existing@example.com',
            'name': 'New User',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!'
        }
        serializer = UserRegistrationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_login_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        from core.serializers import UserLoginSerializer
        
        # Create user
        User.objects.create_user(
            email='test@example.com',
            password='correctpass',
            name='Test'
        )
        
        data = {
            'email': 'test@example.com',
            'password': 'wrongpass'
        }
        serializer = UserLoginSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())


# =============================================================================
# INTEGRATION TESTS - API Flow
# =============================================================================

class AuthenticationAPITests(APITestCase):
    """Integration tests for authentication flow."""
    
    def test_register_returns_jwt_tokens(self):
        """Test registration returns access and refresh tokens."""
        url = '/api/register/'
        data = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')
    
    def test_login_returns_jwt_tokens(self):
        """Test login returns access and refresh tokens."""
        # Create user first
        User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            name='Test'
        )
        
        url = '/api/login/'
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
    
    def test_full_auth_flow(self):
        """Test complete flow: register -> login -> access protected route."""
        # Step 1: Register
        register_url = '/api/register/'
        register_data = {
            'email': 'flowtest@example.com',
            'name': 'Flow Test',
            'password': 'FlowPass123!',
            'password_confirm': 'FlowPass123!'
        }
        
        register_response = self.client.post(register_url, register_data, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Login
        login_url = '/api/login/'
        login_data = {
            'email': 'flowtest@example.com',
            'password': 'FlowPass123!'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        access_token = login_response.data['tokens']['access']
        
        # Step 3: Access protected route
        profile_url = '/api/profile/'
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['email'], 'flowtest@example.com')
    
    def test_protected_route_without_token(self):
        """Test protected route returns 401 without token."""
        url = '/api/profile/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_route_with_invalid_token(self):
        """Test protected route returns 401 with invalid token."""
        url = '/api/profile/'
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_here')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
