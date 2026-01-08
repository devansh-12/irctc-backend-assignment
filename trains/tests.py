"""
Comprehensive tests for trains app.
Tests cover: Model constraints, Seat availability logic, Search API, Admin-only access.
"""
from decimal import Decimal
from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from trains.models import Train, TrainSchedule, SeatAvailability

User = get_user_model()


# UNIT TESTS - Models

class TrainModelTests(TestCase):
    """Test Train model constraints."""
    
    def test_create_train(self):
        """Test creating a train is successful."""
        train = Train.objects.create(
            train_number='12345',
            train_name='Express Train',
            total_seats=100
        )
        
        self.assertEqual(train.train_number, '12345')
        self.assertEqual(train.total_seats, 100)
        self.assertTrue(train.is_active)
    
    def test_train_number_unique(self):
        """Test train number must be unique."""
        Train.objects.create(
            train_number='UNIQUE001',
            train_name='Train 1',
            total_seats=100
        )
        
        with self.assertRaises(Exception):
            Train.objects.create(
                train_number='UNIQUE001',
                train_name='Train 2',
                total_seats=200
            )
    
    def test_train_string_representation(self):
        """Test Train __str__ format."""
        train = Train.objects.create(
            train_number='12951',
            train_name='Mumbai Rajdhani',
            total_seats=500
        )
        
        self.assertEqual(str(train), '12951 - Mumbai Rajdhani')


class TrainScheduleModelTests(TestCase):
    """Test TrainSchedule model."""
    
    def setUp(self):
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=100
        )
    
    def test_create_schedule(self):
        """Test creating a train schedule."""
        schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(16, 55),
            arrival_time=time(8, 35),
            base_fare=Decimal('2500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        
        self.assertEqual(schedule.source, 'Delhi')
        self.assertEqual(schedule.destination, 'Mumbai')
        self.assertTrue(schedule.is_active)


class SeatAvailabilityTests(TestCase):
    """Test seat availability logic."""
    
    def setUp(self):
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=10  # Small number for testing
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(16, 55),
            arrival_time=time(8, 35),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        self.availability = SeatAvailability.objects.create(
            schedule=self.schedule,
            booked_seats=0
        )
    
    def test_available_seats_calculation(self):
        """Test available_seats property calculates correctly."""
        self.assertEqual(self.availability.available_seats, 10)
        
        self.availability.booked_seats = 3
        self.availability.save()
        
        self.assertEqual(self.availability.available_seats, 7)
    
    def test_can_book_with_available_seats(self):
        """Test can_book returns True when seats available."""
        self.assertTrue(self.availability.can_book(5))
        self.assertTrue(self.availability.can_book(10))
    
    def test_can_book_exceeds_available(self):
        """Test can_book returns False when requesting too many seats."""
        self.assertFalse(self.availability.can_book(11))
        
        self.availability.booked_seats = 8
        self.availability.save()
        
        self.assertFalse(self.availability.can_book(3))  # Only 2 available
    
    def test_optimistic_locking_version(self):
        """Test version field increments for optimistic locking."""
        initial_version = self.availability.version
        
        # Simulate concurrent update using version check
        updated = SeatAvailability.objects.filter(
            id=self.availability.id,
            version=initial_version
        ).update(
            booked_seats=5,
            version=initial_version + 1
        )
        
        self.assertEqual(updated, 1)  # One row updated
        
        # Refresh from DB
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.version, initial_version + 1)
        self.assertEqual(self.availability.booked_seats, 5)


# INTEGRATION TESTS - Train Search API

class TrainSearchAPITests(APITestCase):
    """Integration tests for train search API."""
    
    def setUp(self):
        # Create regular user
        self.user = User.objects.create_user(
            email='user@example.com',
            password='UserPass123!',
            name='Regular User'
        )
        
        # Create train and schedule
        self.train = Train.objects.create(
            train_number='12951',
            train_name='Mumbai Rajdhani',
            total_seats=500
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(16, 55),
            arrival_time=time(8, 35),
            base_fare=Decimal('2500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        SeatAvailability.objects.create(
            schedule=self.schedule,
            booked_seats=0
        )
        
        # Login and get token
        response = self.client.post('/api/login/', {
            'email': 'user@example.com',
            'password': 'UserPass123!'
        }, format='json')
        self.token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_search_trains_success(self):
        """Test searching trains between stations."""
        url = '/api/trains/search/'
        response = self.client.get(url, {
            'source': 'Delhi',
            'destination': 'Mumbai'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['train_number'], '12951')
    
    def test_search_trains_case_insensitive(self):
        """Test search is case insensitive."""
        url = '/api/trains/search/'
        response = self.client.get(url, {
            'source': 'DELHI',
            'destination': 'mumbai'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_search_trains_no_results(self):
        """Test search with no matching trains."""
        url = '/api/trains/search/'
        response = self.client.get(url, {
            'source': 'Chennai',
            'destination': 'Kolkata'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
    
    def test_search_trains_missing_params(self):
        """Test search fails without required params."""
        url = '/api/trains/search/'
        response = self.client.get(url, {'source': 'Delhi'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_search_with_date_filter(self):
        """Test search with date filter."""
        url = '/api/trains/search/'
        future_date = (date.today() + timedelta(days=7)).isoformat()
        
        response = self.client.get(url, {
            'source': 'Delhi',
            'destination': 'Mumbai',
            'date': future_date
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_search_with_pagination(self):
        """Test search pagination with limit and offset."""
        url = '/api/trains/search/'
        response = self.client.get(url, {
            'source': 'Delhi',
            'destination': 'Mumbai',
            'limit': 5,
            'offset': 0
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('limit', response.data)
        self.assertIn('offset', response.data)
    
    def test_search_unauthenticated(self):
        """Test search fails without authentication."""
        self.client.credentials()  # Remove credentials
        url = '/api/trains/search/'
        response = self.client.get(url, {
            'source': 'Delhi',
            'destination': 'Mumbai'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



# INTEGRATION TESTS - Admin Only Access

class AdminOnlyAPITests(APITestCase):
    """Test admin-only route access control."""
    
    def setUp(self):
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='UserPass123!',
            name='Regular User'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            name='Admin User'
        )
        self.admin_user.is_admin = True
        self.admin_user.save()
    
    def get_token(self, email, password):
        """Helper to get JWT token."""
        response = self.client.post('/api/login/', {
            'email': email,
            'password': password
        }, format='json')
        return response.data['tokens']['access']
    
    def test_regular_user_cannot_create_train(self):
        """Test regular user gets 403 on admin route."""
        token = self.get_token('user@example.com', 'UserPass123!')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/trains/'
        data = {
            'train_number': '12345',
            'train_name': 'Test Train',
            'total_seats': 100,
            'source': 'Delhi',
            'destination': 'Mumbai',
            'departure_time': '10:00:00',
            'arrival_time': '18:00:00',
            'base_fare': 1000,
            'runs_on': (date.today() + timedelta(days=7)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_create_train(self):
        """Test admin user can create train."""
        token = self.get_token('admin@example.com', 'AdminPass123!')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/trains/'
        data = {
            'train_number': '12345',
            'train_name': 'Test Train',
            'total_seats': 100,
            'source': 'Delhi',
            'destination': 'Mumbai',
            'departure_time': '10:00:00',
            'arrival_time': '18:00:00',
            'base_fare': 1000,
            'runs_on': (date.today() + timedelta(days=7)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['train']['train_number'], '12345')
    
    def test_admin_can_list_trains(self):
        """Test admin can list all trains."""
        # Create a train first
        Train.objects.create(
            train_number='99999',
            train_name='Existing Train',
            total_seats=200
        )
        
        token = self.get_token('admin@example.com', 'AdminPass123!')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/trains/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_unauthenticated_cannot_access_admin_route(self):
        """Test unauthenticated request gets 401."""
        url = '/api/trains/'
        response = self.client.post(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
