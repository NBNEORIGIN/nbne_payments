from django.test import TestCase, Client
from django.conf import settings
from unittest.mock import patch, MagicMock
import json
from .models import Customer, PaymentSession, Transaction, Refund


class PaymentSessionIdempotencyTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.idempotency_key = "test-key-123"

    @patch('payments.views.stripe.checkout.Session.create')
    @patch('payments.views.stripe.Customer.create')
    def test_idempotency_key_prevents_duplicate_sessions(self, mock_customer_create, mock_session_create):
        mock_customer_create.return_value = MagicMock(id='cus_test123')
        mock_session_create.return_value = MagicMock(
            id='cs_test123',
            url='https://checkout.stripe.com/test',
            payment_intent='pi_test123'
        )

        payload = {
            'payable_type': 'booking',
            'payable_id': '1',
            'amount_pence': 1000,
            'currency': 'GBP',
            'customer': {
                'email': 'test@example.com',
                'name': 'Test User'
            },
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
            'idempotency_key': self.idempotency_key,
        }

        response1 = self.client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        data1 = response1.json()
        self.assertIn('checkout_url', data1)
        self.assertEqual(mock_session_create.call_count, 1)

        response2 = self.client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(data1['payment_session_id'], data2['payment_session_id'])
        self.assertEqual(mock_session_create.call_count, 1)

    def test_missing_idempotency_key_returns_error(self):
        payload = {
            'payable_type': 'booking',
            'payable_id': '1',
            'amount_pence': 1000,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        }

        response = self.client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())


class PaymentSessionStatusTransitionTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            email='test@example.com',
            name='Test User',
            provider_customer_id='cus_test123'
        )
        self.payment_session = PaymentSession.objects.create(
            payable_type='booking',
            payable_id='1',
            amount_pence=1000,
            currency='GBP',
            status='created',
            customer=self.customer,
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel',
            idempotency_key='test-key-456',
            stripe_checkout_session_id='cs_test456',
            stripe_payment_intent_id='pi_test456'
        )

    def test_status_transitions_from_created_to_pending(self):
        self.assertEqual(self.payment_session.status, 'created')
        self.payment_session.status = 'pending'
        self.payment_session.save()
        self.payment_session.refresh_from_db()
        self.assertEqual(self.payment_session.status, 'pending')

    def test_status_transitions_to_succeeded(self):
        self.payment_session.status = 'pending'
        self.payment_session.save()
        
        self.payment_session.status = 'succeeded'
        self.payment_session.save()
        self.payment_session.refresh_from_db()
        self.assertEqual(self.payment_session.status, 'succeeded')

    def test_transaction_created_on_success(self):
        self.payment_session.status = 'succeeded'
        self.payment_session.save()

        transaction = Transaction.objects.create(
            payment_session=self.payment_session,
            gross_amount_pence=self.payment_session.amount_pence,
            currency=self.payment_session.currency,
            provider_charge_id='ch_test123'
        )

        self.assertEqual(transaction.payment_session, self.payment_session)
        self.assertEqual(transaction.gross_amount_pence, 1000)

    def test_event_idempotency(self):
        event_id = 'evt_test123'
        
        result1 = self.payment_session.mark_event_processed(event_id)
        self.assertTrue(result1)
        self.assertIn(event_id, self.payment_session.processed_events)

        result2 = self.payment_session.mark_event_processed(event_id)
        self.assertFalse(result2)


class WebhookSignatureTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_webhook_rejects_missing_signature(self):
        payload = json.dumps({'type': 'checkout.session.completed'})
        response = self.client.post(
            '/api/payments/webhook/stripe/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    @patch('payments.views.stripe.Webhook.construct_event')
    def test_webhook_rejects_invalid_signature(self, mock_construct_event):
        import stripe
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            'Invalid signature', 'sig_header'
        )

        payload = json.dumps({'type': 'checkout.session.completed'})
        response = self.client.post(
            '/api/payments/webhook/stripe/',
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_signature'
        )
        self.assertEqual(response.status_code, 400)


class PaymentValidationTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_negative_amount_rejected(self):
        payload = {
            'payable_type': 'booking',
            'payable_id': '1',
            'amount_pence': -1000,
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
            'idempotency_key': 'test-key-789',
        }

        response = self.client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Amount must be >= 0', response.json()['error'])

    def test_missing_required_fields(self):
        payload = {
            'payable_type': 'booking',
        }

        response = self.client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Missing required fields', response.json()['error'])


class CustomerCreationTest(TestCase):
    @patch('payments.views.stripe.checkout.Session.create')
    @patch('payments.views.stripe.Customer.create')
    def test_customer_created_with_stripe_id(self, mock_customer_create, mock_session_create):
        mock_customer_create.return_value = MagicMock(id='cus_new123')
        mock_session_create.return_value = MagicMock(
            id='cs_new123',
            url='https://checkout.stripe.com/test',
            payment_intent='pi_new123'
        )

        client = Client()
        payload = {
            'payable_type': 'booking',
            'payable_id': '1',
            'amount_pence': 1000,
            'customer': {
                'email': 'newcustomer@example.com',
                'name': 'New Customer',
                'phone': '+44123456789'
            },
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
            'idempotency_key': 'test-key-new',
        }

        response = client.post(
            '/api/payments/checkout/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        customer = Customer.objects.get(email='newcustomer@example.com')
        self.assertEqual(customer.name, 'New Customer')
        self.assertEqual(customer.provider_customer_id, 'cus_new123')
