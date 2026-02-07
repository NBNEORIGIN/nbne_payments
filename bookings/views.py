import json
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .models import Booking
from payments.views import create_checkout_session_internal, get_payment_status_internal


@csrf_exempt
@require_http_methods(["POST"])
def create_booking(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    customer_name = data.get('customer_name')
    customer_email = data.get('customer_email')
    customer_phone = data.get('customer_phone', '')
    service_name = data.get('service_name')
    booking_date = data.get('booking_date')
    total_amount_pence = data.get('total_amount_pence')
    deposit_amount_pence = data.get('deposit_amount_pence', 0)
    notes = data.get('notes', '')
    frontend_success_url = data.get('success_url')
    frontend_cancel_url = data.get('cancel_url')

    if any(v is None for v in [customer_name, customer_email, service_name, booking_date, total_amount_pence]):
        return JsonResponse({
            'error': 'Missing required fields: customer_name, customer_email, service_name, booking_date, total_amount_pence'
        }, status=400)

    with transaction.atomic():
        booking = Booking.objects.create(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            service_name=service_name,
            booking_date=booking_date,
            total_amount_pence=total_amount_pence,
            deposit_amount_pence=deposit_amount_pence,
            notes=notes,
            status='PENDING_PAYMENT' if deposit_amount_pence > 0 and settings.PAYMENTS_ENABLED else 'CONFIRMED',
        )

        if deposit_amount_pence > 0 and settings.PAYMENTS_ENABLED:
            try:
                idempotency_key = f"booking-{booking.id}-{uuid.uuid4()}"
                
                success_url = frontend_success_url or f"{request.scheme}://{request.get_host()}/api/bookings/{booking.id}/payment-success/?session_id={{CHECKOUT_SESSION_ID}}"
                cancel_url = frontend_cancel_url or f"{request.scheme}://{request.get_host()}/api/bookings/{booking.id}/payment-cancel/"

                payment_data = {
                    'payable_type': 'booking',
                    'payable_id': str(booking.id),
                    'amount_pence': deposit_amount_pence,
                    'currency': settings.DEFAULT_CURRENCY,
                    'customer': {
                        'email': customer_email,
                        'name': customer_name,
                        'phone': customer_phone,
                    },
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                    'metadata': {
                        'service_name': service_name,
                        'booking_date': booking_date,
                        'deposit_pct': int((deposit_amount_pence / total_amount_pence) * 100) if total_amount_pence > 0 else 0,
                    },
                    'idempotency_key': idempotency_key,
                }

                payment_response = create_checkout_session_internal(payment_data)
                return JsonResponse({
                    'booking_id': booking.id,
                    'status': booking.status,
                    'checkout_url': payment_response.get('checkout_url'),
                    'payment_session_id': payment_response.get('payment_session_id'),
                }, status=201)

            except ValueError as e:
                booking.status = 'CANCELLED'
                booking.notes += f"\n[Payment validation error: {str(e)}]"
                booking.save()
                return JsonResponse({
                    'error': f'Payment validation error: {str(e)}',
                    'booking_id': booking.id,
                }, status=400)
            except Exception as e:
                booking.status = 'CANCELLED'
                booking.notes += f"\n[Payment error: {str(e)}]"
                booking.save()
                return JsonResponse({
                    'error': f'Payment system error: {str(e)}',
                    'booking_id': booking.id,
                }, status=500)

        return JsonResponse({
            'booking_id': booking.id,
            'status': booking.status,
            'message': 'Booking confirmed without payment' if not deposit_amount_pence else 'Booking created',
        }, status=201)


@require_http_methods(["GET"])
def get_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        return JsonResponse({
            'booking_id': booking.id,
            'customer_name': booking.customer_name,
            'customer_email': booking.customer_email,
            'service_name': booking.service_name,
            'booking_date': booking.booking_date.isoformat(),
            'total_amount_pence': booking.total_amount_pence,
            'deposit_amount_pence': booking.deposit_amount_pence,
            'status': booking.status,
            'notes': booking.notes,
        })
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def confirm_booking_payment(request, booking_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    payment_session_id = data.get('payment_session_id')

    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

    if not payment_session_id:
        return JsonResponse({'error': 'payment_session_id required'}, status=400)

    try:
        payment_data = get_payment_status_internal(payment_session_id)

        if payment_data.get('status') == 'succeeded' and payment_data.get('payable_id') == str(booking_id):
            booking.status = 'CONFIRMED'
            booking.save(update_fields=['status', 'updated_at'])
            return JsonResponse({
                'booking_id': booking.id,
                'status': booking.status,
                'message': 'Payment confirmed, booking is now confirmed'
            })
        else:
            return JsonResponse({
                'booking_id': booking.id,
                'status': booking.status,
                'payment_status': payment_data.get('status'),
                'message': 'Payment not yet completed'
            })

    except Exception as e:
        return JsonResponse({'error': f'Payment verification error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook_callback(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    payable_type = data.get('payable_type')
    payable_id = data.get('payable_id')
    payment_status = data.get('status')

    if payable_type != 'booking':
        return JsonResponse({'message': 'Not a booking payment'})

    try:
        booking = Booking.objects.get(id=payable_id)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

    if payment_status == 'succeeded':
        booking.status = 'CONFIRMED'
        booking.save(update_fields=['status', 'updated_at'])
    elif payment_status in ['failed', 'canceled']:
        booking.status = 'CANCELLED'
        booking.notes += f"\n[Payment {payment_status}]"
        booking.save(update_fields=['status', 'notes', 'updated_at'])

    return JsonResponse({'message': 'Booking updated'})


@require_http_methods(["GET"])
def payment_success(request, booking_id):
    session_id = request.GET.get('session_id')
    
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

    return JsonResponse({
        'message': 'Payment successful',
        'booking_id': booking.id,
        'session_id': session_id,
        'next_step': f'Call POST /api/bookings/{booking_id}/confirm-payment/ with payment_session_id to confirm booking'
    })


@require_http_methods(["GET"])
def payment_cancel(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        booking.status = 'CANCELLED'
        booking.notes += '\n[Payment cancelled by user]'
        booking.save(update_fields=['status', 'notes', 'updated_at'])
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

    return JsonResponse({
        'message': 'Payment cancelled',
        'booking_id': booking.id,
        'status': booking.status
    })
