"""
Management command to seed the database with sample data.

Usage:
    python manage.py seed_db           # Seed with default data
    python manage.py seed_db --clear   # Clear existing data first
"""
from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import User
from trains.models import Train, TrainSchedule, SeatAvailability
from bookings.models import Booking, Passenger


class Command(BaseCommand):
    help = 'Seed the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Seeding database...')
        
        with transaction.atomic():
            users = self.create_users()
            trains = self.create_trains()
            schedules = self.create_schedules(trains)
            self.create_sample_bookings(users, schedules)

        self.stdout.write(self.style.SUCCESS('✓ Database seeded successfully!'))
        self.print_summary()

    def clear_data(self):
        Passenger.objects.all().delete()
        Booking.objects.all().delete()
        SeatAvailability.objects.all().delete()
        TrainSchedule.objects.all().delete()
        Train.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING('  Cleared all non-superuser data'))

    def create_users(self):
        users = []
        
        # Admin user
        admin, created = User.objects.get_or_create(
            email='admin@irctc.com',
            defaults={
                'name': 'Admin User',
                'is_admin': True,
                'is_staff': True,
            }
        )
        if created:
            admin.set_password('Admin@123')
            admin.save()
            self.stdout.write(f'  Created admin: admin@irctc.com / Admin@123')
        users.append(admin)

        # Regular users
        test_users = [
            ('john@example.com', 'John Doe', 'User@123'),
            ('jane@example.com', 'Jane Smith', 'User@123'),
            ('raj@example.com', 'Raj Kumar', 'User@123'),
        ]
        
        for email, name, password in test_users:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'name': name}
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created user: {email} / {password}')
            users.append(user)

        return users

    def create_trains(self):
        trains_data = [
            ('12951', 'Mumbai Rajdhani', 500),
            ('12301', 'Howrah Rajdhani', 450),
            ('12302', 'New Delhi Rajdhani', 450),
            ('12259', 'Sealdah Duronto', 400),
            ('22691', 'Bangalore Rajdhani', 350),
            ('12627', 'Karnataka Express', 600),
            ('12621', 'Tamil Nadu Express', 550),
            ('12309', 'Rajdhani Express', 400),
            ('12381', 'Poorva Express', 500),
            ('12245', 'Shatabdi Express', 300),
        ]
        
        trains = []
        for number, name, seats in trains_data:
            train, created = Train.objects.get_or_create(
                train_number=number,
                defaults={'train_name': name, 'total_seats': seats}
            )
            trains.append(train)
            if created:
                self.stdout.write(f'  Created train: {number} - {name}')
        
        return trains

    def create_schedules(self, trains):
        routes = [
            ('Delhi', 'Mumbai', time(16, 55), time(8, 35), Decimal('2500.00')),
            ('Delhi', 'Kolkata', time(17, 0), time(10, 0), Decimal('2200.00')),
            ('Delhi', 'Chennai', time(15, 30), time(7, 0), Decimal('2800.00')),
            ('Delhi', 'Bangalore', time(20, 0), time(6, 30), Decimal('2600.00')),
            ('Mumbai', 'Delhi', time(17, 0), time(8, 35), Decimal('2500.00')),
            ('Mumbai', 'Bangalore', time(23, 0), time(6, 0), Decimal('1500.00')),
            ('Chennai', 'Bangalore', time(6, 0), time(11, 0), Decimal('800.00')),
            ('Kolkata', 'Delhi', time(14, 0), time(8, 0), Decimal('2200.00')),
            ('Bangalore', 'Chennai', time(14, 30), time(19, 30), Decimal('800.00')),
            ('Mumbai', 'Chennai', time(11, 0), time(9, 0), Decimal('1800.00')),
        ]
        
        schedules = []
        today = date.today()
        
        for i, train in enumerate(trains):
            route = routes[i % len(routes)]
            source, dest, dep, arr, fare = route
            
            # Create schedules for next 7 days
            for day_offset in range(7):
                run_date = today + timedelta(days=day_offset + 1)
                
                schedule, created = TrainSchedule.objects.get_or_create(
                    train=train,
                    runs_on=run_date,
                    defaults={
                        'source': source,
                        'destination': dest,
                        'departure_time': dep,
                        'arrival_time': arr,
                        'base_fare': fare,
                    }
                )
                
                if created:
                    SeatAvailability.objects.create(schedule=schedule, booked_seats=0)
                    schedules.append(schedule)
        
        self.stdout.write(f'  Created {len(schedules)} train schedules')
        return schedules

    def create_sample_bookings(self, users, schedules):
        if not schedules:
            return
        
        # Create a few sample bookings
        regular_users = [u for u in users if not u.is_admin]
        
        bookings_created = 0
        for i, user in enumerate(regular_users[:2]):
            schedule = schedules[i] if i < len(schedules) else schedules[0]
            
            booking = Booking.objects.create(
                user=user,
                schedule=schedule,
                num_passengers=2,
                total_fare=schedule.base_fare * 2,
                status='CONFIRMED'
            )
            
            # Add passengers
            Passenger.objects.create(
                booking=booking,
                name=user.name,
                age=30,
                gender='M',
                seat_number=1
            )
            Passenger.objects.create(
                booking=booking,
                name=f'{user.name} Jr',
                age=25,
                gender='M',
                seat_number=2
            )
            
            # Update seat availability
            availability = schedule.availability
            availability.booked_seats += 2
            availability.save()
            
            bookings_created += 1
        
        self.stdout.write(f'  Created {bookings_created} sample bookings')

    def print_summary(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Database Summary:')
        self.stdout.write(f'  Users: {User.objects.count()}')
        self.stdout.write(f'  Trains: {Train.objects.count()}')
        self.stdout.write(f'  Schedules: {TrainSchedule.objects.count()}')
        self.stdout.write(f'  Bookings: {Booking.objects.count()}')
        self.stdout.write('='*50)
        self.stdout.write('\nTest Credentials:')
        self.stdout.write('  Admin: admin@irctc.com / Admin@123')
        self.stdout.write('  User:  john@example.com / User@123')
        self.stdout.write('='*50 + '\n')
