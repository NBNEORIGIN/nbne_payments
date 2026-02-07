import json
import stripe
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .models import Customer, PaymentSession, Transaction, Refund


stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_http_methods(["POST"])
def create_checkout_session(request):
    if not settings.PAYMENTS_ENABLED:
        return JsonResponse({
            'error': 'Payments are not enabled for this instance'
        }, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    payable_type = data.get('payable_type')
    payable_id = data.get('payable_id')
    amount_pence = data.get('amount_pence')
    currency = data.get('currency', settings.DEFAULT_CURRENCY)
    success_url = data.get('success_url')
    cancel_url = data.get('cancel_url')
    idempotency_key = data.get('idempotency_key')
    customer_data = data.get('customer', {})
    metadata = data.get('metadata', {})

    if not all([payable_type, payable_id, amount_pence, success_url, cancel_url, idempotency_key]):
        return JsonResponse({
            'error': 'Missing required fields: payable_type, payable_id, amount_pence, success_url, cancel_url, idempotency_key'
        }, status=400)

    if amount_pence < 0:
        return JsonResponse({'error': 'Amount must be >= 0'}, status=400)

    with transaction.atomic():
        existing_session = PaymentSession.objects.filter(idempotency_key=idempotency_key).first()
        if existing_session:
            checkout_url = f"https://checkout.stripe.com/c/pay/{existing_session.stripe_checkout_session_id}" if existing_session.stripe_checkout_session_id else None
            return JsonResponse({
                'checkout_url': checkout_url,
                'payment_session_id': str(existing_session.id),
                'status': existing_session.status
            })

        customer = None
        if customer_data and customer_data.get('email'):
            customer, created = Customer.objects.get_or_create(
                email=customer_data['email'],
                defaults={
                    'name': customer_data.get('name', ''),
                    'phone': customer_data.get('phone', ''),
                }
            )

            if not customer.provider_customer_id:
                try:
                    stripe_customer = stripe.Customer.create(
                        email=customer.email,
                        name=customer.name,
                        phone=customer.phone,
                    )
                    customer.provider_customer_id = stripe_customer.id
                    customer.save(update_fields=['provider_customer_id'])
                except stripe.error.StripeError as e:
                    pass

        payment_session = PaymentSession.objects.create(
            payable_type=payable_type,
            payable_id=str(payable_id),
            amount_pence=amount_pence,
            currency=currency,
            status='created',
            customer=customer,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        try:
            checkout_metadata = {
                'payable_type': payable_type,
                'payable_id': str(payable_id),
                'payment_session_id': str(payment_session.id),
            }
            checkout_metadata.update(metadata)

            stripe_session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': currency.lower(),
                        'unit_amount': amount_pence,
                        'product_data': {
                            'name': f'{payable_type.title()} Payment',
                            'description': f'Payment for {payable_type} #{payable_id}',
                        },
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': checkout_metadata,
            }

            if customer and customer.provider_customer_id:
                stripe_session_params['customer'] = customer.provider_customer_id

            checkout_session = stripe.checkout.Session.create(**stripe_session_params)

            payment_session.stripe_checkout_session_id = checkout_session.id
            payment_session.stripe_payment_intent_id = checkout_session.payment_intent
            payment_session.status = 'pending'
            payment_session.save(update_fields=['stripe_checkout_session_id', 'stripe_payment_intent_id', 'status'])

            return JsonResponse({
                'checkout_url': checkout_session.url,
                'payment_session_id': str(payment_session.id),
                'status': payment_session.status
            })

        except stripe.error.StripeError as e:
            payment_session.status = 'failed'
            payment_session.metadata['error'] = str(e)
            payment_session.save(update_fields=['status', 'metadata'])
            return JsonResponse({'error': f'Stripe error: {str(e)}'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Webhook secret not configured'}, status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    event_id = event['id']
    event_type = event['type']

    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session, event_id)

    elif event_type == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_intent_succeeded(payment_intent, event_id)

    elif event_type == 'checkout.session.expired':
        session = event['data']['object']
        handle_checkout_expired(session, event_id)

    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failed(payment_intent, event_id)

    elif event_type == 'charge.refunded':
        charge = event['data']['object']
        handle_charge_refunded(charge, event_id)

    return HttpResponse(status=200)


def handle_checkout_completed(session, event_id):
    checkout_session_id = session['id']
    payment_intent_id = session.get('payment_intent')

    with transaction.atomic():
        payment_session = PaymentSession.objects.filter(
            stripe_checkout_session_id=checkout_session_id
        ).select_for_update().first()

        if not payment_session:
            return

        if not payment_session.mark_event_processed(event_id):
            return

        payment_session.status = 'succeeded'
        payment_session.stripe_payment_intent_id = payment_intent_id
        payment_session.save(update_fields=['status', 'stripe_payment_intent_id', 'updated_at'])

        Transaction.objects.create(
            payment_session=payment_session,
            gross_amount_pence=payment_session.amount_pence,
            currency=payment_session.currency,
            provider_charge_id=session.get('payment_intent'),
        )

        trigger_callback(payment_session)


def handle_payment_intent_succeeded(payment_intent, event_id):
    payment_intent_id = payment_intent['id']

    with transaction.atomic():
        payment_session = PaymentSession.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).select_for_update().first()

        if not payment_session:
            return

        if not payment_session.mark_event_processed(event_id):
            return

        if payment_session.status != 'succeeded':
            payment_session.status = 'succeeded'
            payment_session.save(update_fields=['status', 'updated_at'])

            if not payment_session.transactions.exists():
                Transaction.objects.create(
                    payment_session=payment_session,
                    gross_amount_pence=payment_session.amount_pence,
                    currency=payment_session.currency,
                    provider_charge_id=payment_intent_id,
                )

            trigger_callback(payment_session)


def handle_checkout_expired(session, event_id):
    checkout_session_id = session['id']

    with transaction.atomic():
        payment_session = PaymentSession.objects.filter(
            stripe_checkout_session_id=checkout_session_id
        ).select_for_update().first()

        if not payment_session:
            return

        if not payment_session.mark_event_processed(event_id):
            return

        payment_session.status = 'canceled'
        payment_session.save(update_fields=['status', 'updated_at'])

        trigger_callback(payment_session)


def handle_payment_failed(payment_intent, event_id):
    payment_intent_id = payment_intent['id']

    with transaction.atomic():
        payment_session = PaymentSession.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).select_for_update().first()

        if not payment_session:
            return

        if not payment_session.mark_event_processed(event_id):
            return

        payment_session.status = 'failed'
        payment_session.save(update_fields=['status', 'updated_at'])

        trigger_callback(payment_session)


def handle_charge_refunded(charge, event_id):
    charge_id = charge['id']
    refunds = charge.get('refunds', {}).get('data', [])

    with transaction.atomic():
        transactions = Transaction.objects.filter(provider_charge_id=charge_id).select_for_update()

        for txn in transactions:
            payment_session = txn.payment_session

            if not payment_session.mark_event_processed(event_id):
                continue

            payment_session.status = 'refunded'
            payment_session.save(update_fields=['status', 'updated_at'])

            for refund_data in refunds:
                Refund.objects.get_or_create(
                    provider_refund_id=refund_data['id'],
                    defaults={
                        'transaction': txn,
                        'amount_pence': refund_data['amount'],
                        'status': 'succeeded' if refund_data['status'] == 'succeeded' else 'failed',
                        'reason': refund_data.get('reason', ''),
                    }
                )

            trigger_callback(payment_session)


def trigger_callback(payment_session):
    if not settings.PAYMENTS_WEBHOOK_CALLBACK_URL:
        return

    try:
        callback_data = {
            'payable_type': payment_session.payable_type,
            'payable_id': payment_session.payable_id,
            'payment_session_id': str(payment_session.id),
            'status': payment_session.status,
        }
        requests.post(
            settings.PAYMENTS_WEBHOOK_CALLBACK_URL,
            json=callback_data,
            timeout=5
        )
    except Exception:
        pass


@require_http_methods(["GET"])
def get_payment_status(request, payment_session_id):
    try:
        payment_session = PaymentSession.objects.get(id=payment_session_id)
        return JsonResponse({
            'payment_session_id': str(payment_session.id),
            'payable_type': payment_session.payable_type,
            'payable_id': payment_session.payable_id,
            'status': payment_session.status,
            'amount_pence': payment_session.amount_pence,
            'currency': payment_session.currency,
        })
    except PaymentSession.DoesNotExist:
        return JsonResponse({'error': 'Payment session not found'}, status=404)
