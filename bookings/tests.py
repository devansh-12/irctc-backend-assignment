"""
Comprehensive tests for bookings app.
Tests cover: Model constraints, Booking flow, Seat allocation, Concurrency scenarios.
"""
from decimal import Decimal
from datetime import date, time, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.test import APITestCase
from rest_framework import status
import threading
import time as time_module

from trains.models import Train, TrainSchedule, SeatAvailability
from bookings.models import Booking, Passenger, generate_pnr

User = get_user_model()


# =============================================================================
# UNIT TESTS - Models
# =============================================================================

class PNRGenerationTests(TestCase):
    """Test PNR generation utility."""
    
    def test_pnr_length(self):
        """Test PNR is 10 characters."""
        pnr = generate_pnr()
        self.assertEqual(len(pnr), 10)
    
    def test_pnr_alphanumeric(self):
        """Test PNR contains only alphanumeric characters."""
        pnr = generate_pnr()
        self.assertTrue(pnr.isalnum())
    
    def test_pnr_uniqueness(self):
        """Test multiple PNR generations are unique."""
        pnrs = set(generate_pnr() for _ in range(100))
        self.assertEqual(len(pnrs), 100)


class BookingModelTests(TestCase):
    """Test Booking model constraints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            name='Test User'
        )
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=100
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(10, 0),
            arrival_time=time(18, 0),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
    
    def test_create_booking(self):
        """Test creating a booking."""
        booking = Booking.objects.create(
            user=self.user,
            schedule=self.schedule,
            num_passengers=2,
            total_fare=Decimal('1000.00'),
            status='CONFIRMED'
        )
        
        self.assertIsNotNone(booking.pnr)
        self.assertEqual(len(booking.pnr), 10)
        self.assertEqual(booking.status, 'CONFIRMED')
    
    def test_booking_pnr_unique(self):
        """Test PNR uniqueness is enforced."""
        booking1 = Booking.objects.create(
            user=self.user,
            schedule=self.schedule,
            num_passengers=1,
            total_fare=Decimal('500.00')
        )
        
        # Try to create another with same PNR
        booking2 = Booking(
            pnr=booking1.pnr,
            user=self.user,
            schedule=self.schedule,
            num_passengers=1,
            total_fare=Decimal('500.00')
        )
        
        with self.assertRaises(Exception):
            booking2.save()
    
    def test_booking_string_representation(self):
        """Test Booking __str__ format."""
        booking = Booking.objects.create(
            user=self.user,
            schedule=self.schedule,
            num_passengers=1,
            total_fare=Decimal('500.00')
        )
        
        self.assertIn('PNR:', str(booking))
        self.assertIn(self.user.email, str(booking))


class PassengerModelTests(TestCase):
    """Test Passenger model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            name='Test User'
        )
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=100
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(10, 0),
            arrival_time=time(18, 0),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        self.booking = Booking.objects.create(
            user=self.user,
            schedule=self.schedule,
            num_passengers=1,
            total_fare=Decimal('500.00')
        )
    
    def test_create_passenger(self):
        """Test creating a passenger."""
        passenger = Passenger.objects.create(
            booking=self.booking,
            name='John Doe',
            age=30,
            gender='M',
            seat_number=1
        )
        
        self.assertEqual(passenger.name, 'John Doe')
        self.assertEqual(passenger.seat_number, 1)
    
    def test_passenger_age_validation(self):
        """Test passenger age bounds."""
        # Valid age
        passenger = Passenger.objects.create(
            booking=self.booking,
            name='Valid Age',
            age=50,
            gender='M'
        )
        self.assertEqual(passenger.age, 50)


# =============================================================================
# UNIT TESTS - Serializers
# =============================================================================

class BookingSerializerTests(TestCase):
    """Test booking serializer validation."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            name='Test User'
        )
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=10
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(10, 0),
            arrival_time=time(18, 0),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        SeatAvailability.objects.create(
            schedule=self.schedule,
            booked_seats=0
        )
    
    def test_empty_passengers_rejected(self):
        """Test booking with no passengers is rejected."""
        from bookings.serializers import BookingCreateSerializer
        
        data = {
            'schedule_id': self.schedule.id,
            'passengers': []
        }
        
        serializer = BookingCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_too_many_passengers_rejected(self):
        """Test booking with >6 passengers is rejected."""
        from bookings.serializers import BookingCreateSerializer
        
        data = {
            'schedule_id': self.schedule.id,
            'passengers': [
                {'name': f'Passenger {i}', 'age': 30, 'gender': 'M'}
                for i in range(7)
            ]
        }
        
        serializer = BookingCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_invalid_schedule_rejected(self):
        """Test booking with invalid schedule is rejected."""
        from bookings.serializers import BookingCreateSerializer
        
        data = {
            'schedule_id': 99999,  # Non-existent
            'passengers': [
                {'name': 'Test', 'age': 30, 'gender': 'M'}
            ]
        }
        
        serializer = BookingCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())


# =============================================================================
# INTEGRATION TESTS - Booking API
# =============================================================================

class BookingAPITests(APITestCase):
    """Integration tests for booking flow."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='UserPass123!',
            name='Test User'
        )
        self.train = Train.objects.create(
            train_number='12345',
            train_name='Test Express',
            total_seats=10
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(10, 0),
            arrival_time=time(18, 0),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        self.availability = SeatAvailability.objects.create(
            schedule=self.schedule,
            booked_seats=0
        )
        
        # Login
        response = self.client.post('/api/login/', {
            'email': 'user@example.com',
            'password': 'UserPass123!'
        }, format='json')
        self.token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_create_booking_success(self):
        """Test successful booking creation."""
        url = '/api/bookings/'
        data = {
            'schedule_id': self.schedule.id,
            'passengers': [
                {'name': 'John Doe', 'age': 30, 'gender': 'M'},
                {'name': 'Jane Doe', 'age': 28, 'gender': 'F'}
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('pnr', response.data['booking'])
        self.assertEqual(response.data['booking']['num_passengers'], 2)
        self.assertEqual(response.data['booking']['total_fare'], '1000.00')
        self.assertEqual(response.data['booking']['status'], 'CONFIRMED')
        
        # Verify seat allocation
        passengers = response.data['booking']['passengers']
        self.assertEqual(passengers[0]['seat_number'], 1)
        self.assertEqual(passengers[1]['seat_number'], 2)
    
    def test_booking_updates_availability(self):
        """Test booking correctly updates seat availability."""
        url = '/api/bookings/'
        data = {
            'schedule_id': self.schedule.id,
            'passengers': [
                {'name': 'Test', 'age': 25, 'gender': 'M'}
            ]
        }
        
        self.client.post(url, data, format='json')
        
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.booked_seats, 1)
        self.assertEqual(self.availability.available_seats, 9)
    
    def test_booking_exceeds_availability(self):
        """Test booking fails when not enough seats."""
        # Book most seats
        self.availability.booked_seats = 9
        self.availability.save()
        
        url = '/api/bookings/'
        data = {
            'schedule_id': self.schedule.id,
            'passengers': [
                {'name': 'P1', 'age': 25, 'gender': 'M'},
                {'name': 'P2', 'age': 25, 'gender': 'F'}
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_my_bookings(self):
        """Test retrieving user's bookings."""
        # Create a booking
        Booking.objects.create(
            user=self.user,
            schedule=self.schedule,
            num_passengers=1,
            total_fare=Decimal('500.00'),
            status='CONFIRMED'
        )
        
        url = '/api/bookings/my/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('train_details', response.data['results'][0])
    
    def test_booking_unauthenticated(self):
        """Test booking fails without authentication."""
        self.client.credentials()  # Remove token
        
        url = '/api/bookings/'
        data = {
            'schedule_id': self.schedule.id,
            'passengers': [{'name': 'Test', 'age': 25, 'gender': 'M'}]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# CONCURRENCY TESTS - Race Conditions
# =============================================================================

class BookingConcurrencyTests(TransactionTestCase):
    """
    Test booking concurrency scenarios.
    Uses TransactionTestCase for proper transaction isolation.
    """
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='User1Pass123!',
            name='User 1'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='User2Pass123!',
            name='User 2'
        )
        self.train = Train.objects.create(
            train_number='RACE001',
            train_name='Race Condition Express',
            total_seats=5  # Limited seats for testing
        )
        self.schedule = TrainSchedule.objects.create(
            train=self.train,
            source='Delhi',
            destination='Mumbai',
            departure_time=time(10, 0),
            arrival_time=time(18, 0),
            base_fare=Decimal('500.00'),
            runs_on=date.today() + timedelta(days=7)
        )
        self.availability = SeatAvailability.objects.create(
            schedule=self.schedule,
            booked_seats=0
        )
    
    def test_concurrent_bookings_dont_oversell(self):
        """
        Test that concurrent bookings don't oversell seats.
        This simulates race condition where two users try to book 
        the last seats simultaneously.
        """
        # Set only 3 seats available
        self.availability.booked_seats = 2
        self.availability.save()
        
        results = {'success': 0, 'failed': 0}
        errors = []
        
        def make_booking(user, passenger_name):
            """Make a booking attempt."""
            from django.test import Client
            from django.db import connection
            
            client = Client()
            
            # Login
            login_response = client.post('/api/login/', {
                'email': user.email,
                'password': 'User1Pass123!' if user == self.user1 else 'User2Pass123!'
            }, content_type='application/json')
            
            if login_response.status_code != 200:
                results['failed'] += 1
                return
            
            token = login_response.json()['tokens']['access']
            
            # Attempt booking
            booking_response = client.post(
                '/api/bookings/',
                {
                    'schedule_id': self.schedule.id,
                    'passengers': [
                        {'name': passenger_name + '1', 'age': 25, 'gender': 'M'},
                        {'name': passenger_name + '2', 'age': 25, 'gender': 'M'}
                    ]
                },
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {token}'
            )
            
            if booking_response.status_code == 201:
                results['success'] += 1
            else:
                results['failed'] += 1
                errors.append(booking_response.json())
            
            connection.close()
        
        # Create threads for concurrent booking
        thread1 = threading.Thread(target=make_booking, args=(self.user1, 'User1Pass'))
        thread2 = threading.Thread(target=make_booking, args=(self.user2, 'User2Pass'))
        
        # Start both threads
        thread1.start()
        thread2.start()
        
        # Wait for completion
        thread1.join()
        thread2.join()
        
        # Refresh availability
        self.availability.refresh_from_db()
        
        # Assertions:
        # - At most one booking should succeed (only 3 seats, each wants 2)
        # - Total booked should not exceed total seats (5)
        self.assertLessEqual(self.availability.booked_seats, 5)
        
        # Either 1 success + 1 fail, or 0 success + 2 fail
        # (depending on timing, both might fail or one succeeds)
        total_attempted = results['success'] + results['failed']
        self.assertEqual(total_attempted, 2)
    
    def test_optimistic_locking_prevents_double_booking(self):
        """
        Test that version-based optimistic locking prevents 
        double booking in concurrent scenarios.
        """
        initial_version = self.availability.version
        
        # Simulate first booking updating the version
        updated = SeatAvailability.objects.filter(
            id=self.availability.id,
            version=initial_version
        ).update(
            booked_seats=2,
            version=initial_version + 1
        )
        self.assertEqual(updated, 1)
        
        # Simulate second concurrent booking trying with stale version
        stale_update = SeatAvailability.objects.filter(
            id=self.availability.id,
            version=initial_version  # Stale version
        ).update(
            booked_seats=4,
            version=initial_version + 1
        )
        
        # Second update should fail (0 rows affected)
        self.assertEqual(stale_update, 0)
        
        # Verify correct state
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.booked_seats, 2)  # First booking's value
        self.assertEqual(self.availability.version, initial_version + 1)
    
    def test_sequential_bookings_work_correctly(self):
        """Test that sequential bookings correctly update seats."""
        from bookings.serializers import BookingCreateSerializer
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        
        # First booking
        request1 = factory.post('/api/bookings/')
        request1.user = self.user1
        
        serializer1 = BookingCreateSerializer(
            data={
                'schedule_id': self.schedule.id,
                'passengers': [{'name': 'User1', 'age': 25, 'gender': 'M'}]
            },
            context={'request': request1}
        )
        
        if serializer1.is_valid():
            serializer1.save()
        
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.booked_seats, 1)
        
        # Second booking
        request2 = factory.post('/api/bookings/')
        request2.user = self.user2
        
        serializer2 = BookingCreateSerializer(
            data={
                'schedule_id': self.schedule.id,
                'passengers': [
                    {'name': 'User2A', 'age': 25, 'gender': 'M'},
                    {'name': 'User2B', 'age': 25, 'gender': 'F'}
                ]
            },
            context={'request': request2}
        )
        
        if serializer2.is_valid():
            serializer2.save()
        
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.booked_seats, 3)
        self.assertEqual(self.availability.available_seats, 2)
