from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
import json
from .models import Booking


class BookingCreationTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('bookings.views.requests.post')
    def test_booking_with_deposit_creates_pending_payment(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'checkout_url': 'https://checkout.stripe.com/test',
            'payment_session_id': '42',
            'status': 'pending'
        }
        mock_post.return_value = mock_response

        payload = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_phone': '+44123456789',
            'service_name': 'Premium Service',
            'booking_date': '2026-03-15T14:00:00Z',
            'total_amount_pence': 10000,
            'deposit_amount_pence': 5000,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel'
        }

        response = self.client.post(
            '/api/bookings/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('booking_id', data)
        self.assertEqual(data['status'], 'PENDING_PAYMENT')
        self.assertIn('checkout_url', data)

        booking = Booking.objects.get(id=data['booking_id'])
        self.assertEqual(booking.status, 'PENDING_PAYMENT')
        self.assertEqual(booking.deposit_amount_pence, 5000)

    def test_booking_without_deposit_creates_confirmed(self):
        payload = {
            'customer_name': 'Jane Doe',
            'customer_email': 'jane@example.com',
            'service_name': 'Free Consultation',
            'booking_date': '2026-03-15T14:00:00Z',
            'total_amount_pence': 0,
            'deposit_amount_pence': 0,
        }

        response = self.client.post(
            '/api/bookings/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'CONFIRMED')

        booking = Booking.objects.get(id=data['booking_id'])
        self.assertEqual(booking.status, 'CONFIRMED')


class BookingPaymentConfirmationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.booking = Booking.objects.create(
            customer_name='Test User',
            customer_email='test@example.com',
            service_name='Test Service',
            booking_date='2026-03-15T14:00:00Z',
            total_amount_pence=10000,
            deposit_amount_pence=5000,
            status='PENDING_PAYMENT'
        )

    @patch('bookings.views.requests.get')
    def test_confirm_payment_updates_booking_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'payment_session_id': '42',
            'payable_id': str(self.booking.id),
            'status': 'succeeded'
        }
        mock_get.return_value = mock_response

        payload = {
            'payment_session_id': '42'
        }

        response = self.client.post(
            f'/api/bookings/{self.booking.id}/confirm-payment/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'CONFIRMED')

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMED')


class BookingWebhookCallbackTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.booking = Booking.objects.create(
            customer_name='Test User',
            customer_email='test@example.com',
            service_name='Test Service',
            booking_date='2026-03-15T14:00:00Z',
            total_amount_pence=10000,
            deposit_amount_pence=5000,
            status='PENDING_PAYMENT'
        )

    def test_webhook_callback_confirms_booking_on_success(self):
        payload = {
            'payable_type': 'booking',
            'payable_id': str(self.booking.id),
            'payment_session_id': '42',
            'status': 'succeeded'
        }

        response = self.client.post(
            '/api/bookings/webhook/payment/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMED')

    def test_webhook_callback_cancels_booking_on_failure(self):
        payload = {
            'payable_type': 'booking',
            'payable_id': str(self.booking.id),
            'payment_session_id': '42',
            'status': 'failed'
        }

        response = self.client.post(
            '/api/bookings/webhook/payment/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CANCELLED')
        self.assertIn('Payment failed', self.booking.notes)
