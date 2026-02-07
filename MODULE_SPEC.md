# NBNE Payments Module — Complete Technical Specification

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Payments Module API](#payments-module-api)
5. [Internal Python API](#internal-python-api)
6. [Webhook System](#webhook-system)
7. [Bookings Reference Implementation](#bookings-reference-implementation)
8. [Frontend Reference Implementation](#frontend-reference-implementation)
9. [Integration Guide for New Verticals](#integration-guide-for-new-verticals)
10. [Environment Variables](#environment-variables)
11. [Deployment Architecture](#deployment-architecture)
12. [File Structure](#file-structure)
13. [Key Design Decisions](#key-design-decisions)
14. [Known Constraints](#known-constraints)

---

## 1. Overview

The NBNE Payments Module is a **reusable, generic Django app** that handles Stripe Checkout payments for any "payable" object. It is designed to be dropped into any Django project and connected to any domain model (bookings, appointments, orders, subscriptions, etc.) without modifying the payments code.

### Live URLs

| Component | URL |
|---|---|
| Frontend Demo | https://nbne-payments-demo.netlify.app |
| Backend API | https://web-production-4e861.up.railway.app/api/ |
| Django Admin | https://web-production-4e861.up.railway.app/admin/ |
| GitHub Repo | https://github.com/NBNEORIGIN/nbne_payments |

### Target Verticals

- Hair salon bookings
- Fitness studio class bookings
- Restaurant reservations
- General service bookings
- Any payable entity

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                       │
│  Netlify Static Export — nbne-payments-demo.netlify.app      │
│                                                              │
│  /                    Landing page                           │
│  /booking/new         Booking form → calls backend API       │
│  /booking/success     Post-payment confirmation              │
│  /booking/cancel      Payment cancelled                      │
│  /booking/lookup      Check booking status by ID             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (CORS enabled)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (Django + Gunicorn)                  │
│  Railway — web-production-4e861.up.railway.app               │
│                                                              │
│  ┌─────────────────┐    ┌──────────────────────┐            │
│  │  bookings app   │───▶│   payments app       │            │
│  │  (consumer)     │    │   (generic module)   │            │
│  │                 │    │                      │            │
│  │ create_booking  │    │ create_checkout_     │            │
│  │ get_booking     │    │   session_internal() │            │
│  │ confirm_payment │    │ get_payment_status_  │            │
│  │ webhook_callback│    │   internal()         │            │
│  └─────────────────┘    │ stripe_webhook()     │            │
│                         └──────────┬───────────┘            │
│                                    │                         │
│  ┌─────────────────────────────────┘                        │
│  │  PostgreSQL (Railway managed)                             │
│  │  payments_customer, payments_session,                     │
│  │  payments_transaction, payments_refund,                   │
│  │  bookings_booking                                         │
│  └──────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ Webhook POST
                           │
┌─────────────────────────────────────────────────────────────┐
│                        STRIPE                                │
│  Checkout Sessions, Payment Intents, Webhooks                │
│  Events: checkout.session.completed/expired,                 │
│          payment_intent.succeeded/payment_failed,            │
│          charge.refunded                                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Principle

The **payments app knows nothing about bookings** (or any other consumer). It uses two generic fields to link to any payable object:

- `payable_type` — a string label (e.g. `"booking"`, `"appointment"`, `"order"`)
- `payable_id` — the ID of the payable object as a string

Consumer apps (bookings, appointments, etc.) call the payments module's **internal Python functions** directly — never via HTTP — to avoid single-worker deadlocks.

---

## 3. Data Models

### payments.Customer

| Field | Type | Description |
|---|---|---|
| `email` | EmailField (unique) | Customer email, used as lookup key |
| `name` | CharField | Customer display name |
| `phone` | CharField | Phone number |
| `provider` | CharField | Payment provider (default: `"stripe"`) |
| `provider_customer_id` | CharField | Stripe Customer ID (e.g. `cus_xxx`) |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-set on save |

### payments.PaymentSession

| Field | Type | Description |
|---|---|---|
| `payable_type` | CharField (indexed) | Type of payable object (e.g. `"booking"`) |
| `payable_id` | CharField (indexed) | ID of the payable object |
| `amount_pence` | IntegerField | Amount in pence (e.g. 5000 = £50.00) |
| `currency` | CharField | ISO currency code (default: `"GBP"`) |
| `status` | CharField | One of: `created`, `pending`, `succeeded`, `failed`, `canceled`, `refunded` |
| `provider` | CharField | Payment provider (default: `"stripe"`) |
| `stripe_checkout_session_id` | CharField (unique) | Stripe Checkout Session ID |
| `stripe_payment_intent_id` | CharField | Stripe Payment Intent ID |
| `customer` | ForeignKey → Customer | Linked customer (nullable) |
| `success_url` | TextField | Redirect URL after successful payment |
| `cancel_url` | TextField | Redirect URL if payment cancelled |
| `metadata` | JSONField | Arbitrary metadata dict |
| `idempotency_key` | CharField (unique) | Prevents duplicate session creation |
| `processed_events` | JSONField (list) | List of processed Stripe event IDs (idempotent webhook handling) |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-set on save |

**Status Flow:**
```
created → pending → succeeded
                  → failed
                  → canceled
         succeeded → refunded
```

### payments.Transaction

| Field | Type | Description |
|---|---|---|
| `payment_session` | ForeignKey → PaymentSession | Parent session |
| `gross_amount_pence` | IntegerField | Gross amount charged |
| `fee_amount_pence` | IntegerField (nullable) | Stripe fee |
| `net_amount_pence` | IntegerField (nullable) | Net after fees |
| `currency` | CharField | ISO currency code |
| `captured_at` | DateTimeField | When payment was captured |
| `provider_charge_id` | CharField | Stripe charge/payment_intent ID |

### payments.Refund

| Field | Type | Description |
|---|---|---|
| `transaction` | ForeignKey → Transaction | Parent transaction |
| `amount_pence` | IntegerField | Refund amount |
| `reason` | TextField | Refund reason |
| `status` | CharField | One of: `requested`, `succeeded`, `failed` |
| `provider_refund_id` | CharField | Stripe refund ID |

---

## 4. Payments Module API (HTTP Endpoints)

Base path: `/api/payments/`

### POST `/api/payments/checkout/`

Create a Stripe Checkout Session.

**Request body:**
```json
{
  "payable_type": "booking",
  "payable_id": "42",
  "amount_pence": 5000,
  "currency": "GBP",
  "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://example.com/cancel",
  "idempotency_key": "booking-42-uuid",
  "customer": {
    "email": "john@example.com",
    "name": "John Doe",
    "phone": "+447700900000"
  },
  "metadata": {
    "service_name": "Haircut",
    "booking_date": "2026-03-15"
  }
}
```

**Response (200):**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "payment_session_id": "1",
  "status": "pending"
}
```

### GET `/api/payments/status/<payment_session_id>/`

Get payment status.

**Response (200):**
```json
{
  "payment_session_id": "1",
  "payable_type": "booking",
  "payable_id": "42",
  "status": "succeeded",
  "amount_pence": 5000,
  "currency": "GBP"
}
```

### POST `/api/payments/webhook/stripe/`

Stripe webhook endpoint. Receives events from Stripe, verifies signature, processes idempotently.

**Handled events:**
- `checkout.session.completed` → marks session `succeeded`, creates Transaction, triggers callback
- `checkout.session.expired` → marks session `canceled`, triggers callback
- `payment_intent.succeeded` → marks session `succeeded` (backup for checkout.session.completed)
- `payment_intent.payment_failed` → marks session `failed`, triggers callback
- `charge.refunded` → marks session `refunded`, creates Refund records, triggers callback

---

## 5. Internal Python API

**CRITICAL:** Consumer apps (bookings, appointments, etc.) must call these functions directly — never via HTTP POST to the same server. This avoids deadlocks on single-worker Gunicorn deployments.

### `create_checkout_session_internal(data: dict) -> dict`

**Location:** `payments.views.create_checkout_session_internal`

**Import:**
```python
from payments.views import create_checkout_session_internal
```

**Args (dict keys):**
| Key | Type | Required | Description |
|---|---|---|---|
| `payable_type` | str | Yes | e.g. `"booking"`, `"appointment"`, `"order"` |
| `payable_id` | str | Yes | ID of the payable object |
| `amount_pence` | int | Yes | Amount in pence |
| `currency` | str | No | Default: `settings.DEFAULT_CURRENCY` (`"GBP"`) |
| `success_url` | str | Yes | Redirect after payment. Use `{CHECKOUT_SESSION_ID}` placeholder. |
| `cancel_url` | str | Yes | Redirect if cancelled |
| `idempotency_key` | str | Yes | Unique key to prevent duplicates |
| `customer` | dict | No | `{"email": "...", "name": "...", "phone": "..."}` |
| `metadata` | dict | No | Arbitrary metadata stored on session and sent to Stripe |

**Returns:**
```python
{
    "checkout_url": "https://checkout.stripe.com/...",
    "payment_session_id": "1",
    "status": "pending"
}
```

**Raises:**
- `ValueError` — missing/invalid fields
- `stripe.error.StripeError` — Stripe API failure

**Example usage:**
```python
from payments.views import create_checkout_session_internal

payment_data = {
    'payable_type': 'appointment',
    'payable_id': str(appointment.id),
    'amount_pence': appointment.deposit_pence,
    'currency': 'GBP',
    'customer': {
        'email': appointment.client_email,
        'name': appointment.client_name,
        'phone': appointment.client_phone,
    },
    'success_url': f'https://myapp.com/appointments/{appointment.id}/success?session_id={{CHECKOUT_SESSION_ID}}',
    'cancel_url': f'https://myapp.com/appointments/{appointment.id}/cancel',
    'metadata': {
        'service': appointment.service_name,
        'stylist': appointment.stylist_name,
    },
    'idempotency_key': f'appointment-{appointment.id}-{uuid.uuid4()}',
}

result = create_checkout_session_internal(payment_data)
# result['checkout_url'] → redirect user here
# result['payment_session_id'] → store for later lookup
```

### `get_payment_status_internal(payment_session_id: int) -> dict`

**Location:** `payments.views.get_payment_status_internal`

**Import:**
```python
from payments.views import get_payment_status_internal
```

**Returns:**
```python
{
    "payment_session_id": "1",
    "payable_type": "booking",
    "payable_id": "42",
    "status": "succeeded",
    "amount_pence": 5000,
    "currency": "GBP"
}
```

**Raises:** `PaymentSession.DoesNotExist` if not found.

---

## 6. Webhook System

### How it works

1. Customer pays on Stripe Checkout
2. Stripe sends `checkout.session.completed` event to `/api/payments/webhook/stripe/`
3. Payments module verifies signature, updates PaymentSession to `succeeded`, creates Transaction
4. Payments module calls `trigger_callback()` which POSTs to `PAYMENTS_WEBHOOK_CALLBACK_URL`
5. Consumer app receives callback and updates its own model (e.g. booking → CONFIRMED)

### Callback Payload

The payments module POSTs this JSON to `PAYMENTS_WEBHOOK_CALLBACK_URL`:

```json
{
  "payable_type": "booking",
  "payable_id": "42",
  "payment_session_id": "1",
  "status": "succeeded"
}
```

**Possible `status` values in callbacks:**
- `succeeded` — payment completed
- `failed` — payment failed
- `canceled` — checkout expired or cancelled
- `refunded` — payment refunded

### Consumer Callback Handler Pattern

```python
@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook_callback(request):
    data = json.loads(request.body)
    
    payable_type = data.get('payable_type')
    payable_id = data.get('payable_id')
    status = data.get('status')
    
    if payable_type != 'appointment':  # filter for your type
        return JsonResponse({'message': 'Not my type'})
    
    appointment = Appointment.objects.get(id=payable_id)
    
    if status == 'succeeded':
        appointment.status = 'CONFIRMED'
        appointment.save()
    elif status in ['failed', 'canceled']:
        appointment.status = 'CANCELLED'
        appointment.save()
    
    return JsonResponse({'message': 'Updated'})
```

### Idempotency

- **Session creation:** Uses `idempotency_key` — if the same key is sent twice, returns the existing session
- **Webhook events:** Each event ID is tracked in `processed_events` — duplicate events are silently ignored
- **Database:** Uses `select_for_update()` for row-level locking during webhook processing

---

## 7. Bookings Reference Implementation

The `bookings` app is a **complete working example** of how to integrate with the payments module. Use it as a template for new verticals.

### Model: `bookings.models.Booking`

```python
class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=50, blank=True)
    service_name = models.CharField(max_length=255)
    booking_date = models.DateTimeField()
    total_amount_pence = models.IntegerField()
    deposit_amount_pence = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')
    notes = models.TextField(blank=True)
```

### Endpoints: `/api/bookings/`

| Method | Path | Description |
|---|---|---|
| POST | `/api/bookings/` | Create booking (+ payment if deposit > 0) |
| GET | `/api/bookings/<id>/` | Get booking details |
| POST | `/api/bookings/<id>/confirm-payment/` | Manually confirm payment |
| GET | `/api/bookings/<id>/payment-success/` | Success redirect handler |
| GET | `/api/bookings/<id>/payment-cancel/` | Cancel redirect handler |
| POST | `/api/bookings/webhook/payment/` | Receives payment callbacks |

### Create Booking Flow

```python
# 1. Create the booking record
booking = Booking.objects.create(
    customer_name=name,
    customer_email=email,
    status='PENDING_PAYMENT' if deposit > 0 else 'CONFIRMED',
    ...
)

# 2. If deposit required, create payment session
if deposit > 0:
    result = create_checkout_session_internal({
        'payable_type': 'booking',
        'payable_id': str(booking.id),
        'amount_pence': deposit,
        'customer': {'email': email, 'name': name},
        'success_url': '...',
        'cancel_url': '...',
        'idempotency_key': f'booking-{booking.id}-{uuid.uuid4()}',
    })
    # Return checkout_url to frontend

# 3. Webhook auto-confirms booking when payment succeeds
```

---

## 8. Frontend Reference Implementation

**Stack:** Next.js 16, TypeScript, TailwindCSS, shadcn/ui, Lucide icons

**Deployed to:** Netlify (static export)

### Pages

| Route | File | Description |
|---|---|---|
| `/` | `src/app/page.tsx` | Landing page with "Book Now" CTA |
| `/booking/new` | `src/app/booking/new/page.tsx` | Booking form with service selection |
| `/booking/success` | `src/app/booking/success/page.tsx` | Post-payment confirmation |
| `/booking/cancel` | `src/app/booking/cancel/page.tsx` | Payment cancelled |
| `/booking/lookup` | `src/app/booking/lookup/page.tsx` | Check booking status by ID |

### API Client (`src/lib/api.ts`)

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create a booking (returns checkout_url for redirect)
export async function createBooking(data: BookingRequest): Promise<BookingResponse>

// Get booking details by ID
export async function getBooking(bookingId: number): Promise<BookingDetails>

// Manually confirm payment for a booking
export async function confirmBookingPayment(bookingId: number, paymentSessionId: string): Promise<BookingResponse>

// Format pence to £ string
export function formatPence(pence: number): string
```

### Frontend Flow

1. User fills form on `/booking/new`
2. Frontend POSTs to `/api/bookings/` → gets `checkout_url`
3. Frontend stores `booking_id` in `sessionStorage`, redirects to Stripe Checkout
4. After payment, Stripe redirects to `/booking/success`
5. Success page reads `booking_id` from `sessionStorage`, fetches booking details
6. Webhook has already confirmed the booking by this point

---

## 9. Integration Guide for New Verticals

### Step-by-step: Adding a new vertical (e.g. Hair Salon Appointments)

#### 1. Create the Django app

```bash
python manage.py startapp appointments
```

#### 2. Define the model

```python
# appointments/models.py
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
    ]
    
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=50, blank=True)
    stylist_name = models.CharField(max_length=255)
    service_name = models.CharField(max_length=255)
    appointment_datetime = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    price_pence = models.IntegerField()
    deposit_pence = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 3. Create the views

```python
# appointments/views.py
import json, uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Appointment
from payments.views import create_checkout_session_internal, get_payment_status_internal

@csrf_exempt
@require_http_methods(["POST"])
def create_appointment(request):
    data = json.loads(request.body)
    
    appointment = Appointment.objects.create(
        client_name=data['client_name'],
        client_email=data['client_email'],
        client_phone=data.get('client_phone', ''),
        stylist_name=data['stylist_name'],
        service_name=data['service_name'],
        appointment_datetime=data['appointment_datetime'],
        duration_minutes=data.get('duration_minutes', 60),
        price_pence=data['price_pence'],
        deposit_pence=data.get('deposit_pence', 0),
        status='PENDING_PAYMENT' if data.get('deposit_pence', 0) > 0 else 'CONFIRMED',
    )
    
    if appointment.deposit_pence > 0 and settings.PAYMENTS_ENABLED:
        result = create_checkout_session_internal({
            'payable_type': 'appointment',
            'payable_id': str(appointment.id),
            'amount_pence': appointment.deposit_pence,
            'currency': settings.DEFAULT_CURRENCY,
            'customer': {
                'email': appointment.client_email,
                'name': appointment.client_name,
                'phone': appointment.client_phone,
            },
            'success_url': data.get('success_url', f'https://myapp.com/appointments/{appointment.id}/success?session_id={{CHECKOUT_SESSION_ID}}'),
            'cancel_url': data.get('cancel_url', f'https://myapp.com/appointments/{appointment.id}/cancel'),
            'metadata': {
                'service': appointment.service_name,
                'stylist': appointment.stylist_name,
                'datetime': str(appointment.appointment_datetime),
            },
            'idempotency_key': f'appointment-{appointment.id}-{uuid.uuid4()}',
        })
        
        return JsonResponse({
            'appointment_id': appointment.id,
            'status': appointment.status,
            'checkout_url': result['checkout_url'],
            'payment_session_id': result['payment_session_id'],
        }, status=201)
    
    return JsonResponse({
        'appointment_id': appointment.id,
        'status': appointment.status,
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook_callback(request):
    data = json.loads(request.body)
    
    if data.get('payable_type') != 'appointment':
        return JsonResponse({'message': 'Not an appointment'})
    
    appointment = Appointment.objects.get(id=data['payable_id'])
    
    if data['status'] == 'succeeded':
        appointment.status = 'CONFIRMED'
        appointment.save(update_fields=['status', 'updated_at'])
    elif data['status'] in ['failed', 'canceled']:
        appointment.status = 'CANCELLED'
        appointment.notes += f"\n[Payment {data['status']}]"
        appointment.save(update_fields=['status', 'notes', 'updated_at'])
    
    return JsonResponse({'message': 'Updated'})
```

#### 4. Wire up URLs

```python
# appointments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_appointment, name='create_appointment'),
    path('webhook/payment/', views.payment_webhook_callback, name='appointment_payment_callback'),
]
```

```python
# config/urls.py — add:
path('api/appointments/', include('appointments.urls')),
```

#### 5. Register in settings

```python
# config/settings.py — add to INSTALLED_APPS:
'appointments',
```

#### 6. Set callback URL

```bash
# Railway env var:
PAYMENTS_WEBHOOK_CALLBACK_URL=https://your-app.up.railway.app/api/appointments/webhook/payment/
```

**Note:** If you have multiple consumer apps, you'll need a dispatcher endpoint or use the `payable_type` field to route callbacks.

---

## 10. Environment Variables

### Backend (Railway)

| Variable | Example | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | `7%30a^%5nvk79@...` | Django secret key |
| `DATABASE_URL` | `postgresql://...` | Auto-set by Railway PostgreSQL |
| `STRIPE_SECRET_KEY` | `sk_test_...` | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Stripe webhook signing secret |
| `PAYMENTS_ENABLED` | `True` | Enable/disable payment processing |
| `DEFAULT_CURRENCY` | `GBP` | Default currency for payments |
| `PAYMENTS_WEBHOOK_CALLBACK_URL` | `https://...` | URL to POST payment status updates to |
| `ALLOWED_HOSTS` | `web-production-4e861.up.railway.app` | Django allowed hosts |
| `CORS_ALLOWED_ORIGINS` | `https://nbne-payments-demo.netlify.app,http://localhost:3000` | CORS origins |
| `CSRF_TRUSTED_ORIGINS` | `https://nbne-payments-demo.netlify.app,...` | CSRF trusted origins |
| `DJANGO_SUPERUSER_USERNAME` | `admin` | Auto-created superuser username |
| `DJANGO_SUPERUSER_EMAIL` | `toby@nbnesigns.com` | Auto-created superuser email |
| `DJANGO_SUPERUSER_PASSWORD` | `(secret)` | Auto-created superuser password |
| `DEBUG` | `False` | Django debug mode |

### Frontend (Netlify)

| Variable | Example | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://web-production-4e861.up.railway.app` | Backend API base URL |

---

## 11. Deployment Architecture

### Backend: Railway

- **Runtime:** Python 3.11.7
- **Server:** Gunicorn (1 sync worker)
- **Database:** Railway-managed PostgreSQL
- **Static files:** WhiteNoise (served from `/staticfiles/`)
- **Builder:** Railpack (auto-detects Python)
- **Entrypoint:** `entrypoint.sh` (collectstatic → migrate → ensure_superuser → gunicorn)
- **Procfile:** `web: bash entrypoint.sh`

### Frontend: Netlify

- **Framework:** Next.js 16 (static export)
- **Build:** `npm run build` → outputs to `out/`
- **Config:** `netlify.toml`

### Stripe

- **Mode:** Test (sandbox)
- **Webhook endpoint:** `NBNE Railway Production` → `https://web-production-4e861.up.railway.app/api/payments/webhook/stripe/`
- **Events:** `checkout.session.completed`, `checkout.session.expired`, `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`

---

## 12. File Structure

```
nbne-payments/
├── config/                     # Django project config
│   ├── settings.py             # All settings, env vars, CORS, Stripe config
│   ├── urls.py                 # Root URL routing
│   ├── wsgi.py                 # WSGI entry point
│   └── asgi.py                 # ASGI entry point
│
├── payments/                   # GENERIC PAYMENTS MODULE (reusable)
│   ├── models.py               # Customer, PaymentSession, Transaction, Refund
│   ├── views.py                # Checkout, webhook, status (internal + HTTP)
│   ├── urls.py                 # /api/payments/ routes
│   ├── admin.py                # Django admin config
│   ├── tests.py                # Unit tests
│   └── management/
│       └── commands/
│           └── ensure_superuser.py  # Auto-create admin on deploy
│
├── bookings/                   # REFERENCE CONSUMER APP
│   ├── models.py               # Booking model
│   ├── views.py                # Booking CRUD + payment integration
│   ├── urls.py                 # /api/bookings/ routes
│   ├── admin.py                # Django admin config
│   └── tests.py                # Unit tests
│
├── frontend/                   # NEXT.JS FRONTEND
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                    # Landing page
│   │   │   └── booking/
│   │   │       ├── new/page.tsx            # Booking form
│   │   │       ├── success/page.tsx        # Payment success
│   │   │       ├── cancel/page.tsx         # Payment cancelled
│   │   │       └── lookup/page.tsx         # Status lookup
│   │   ├── components/ui/                  # shadcn/ui components
│   │   └── lib/
│   │       ├── api.ts                      # API client
│   │       └── utils.ts                    # Utility functions
│   ├── netlify.toml                        # Netlify config
│   ├── next.config.ts                      # Next.js config (static export)
│   └── package.json
│
├── entrypoint.sh               # Railway startup script
├── Procfile                    # Railway process definition
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version
├── .env.example                # Environment variable template
└── manage.py                   # Django management
```

---

## 13. Key Design Decisions

1. **Generic payable linkage** — `payable_type` + `payable_id` strings instead of ForeignKey. This means the payments app never imports consumer models and can be dropped into any project.

2. **Internal function calls, not HTTP** — Consumer apps call `create_checkout_session_internal()` directly. This avoids deadlocks when running with a single Gunicorn worker (common on Railway free/hobby tier).

3. **Idempotent everything** — Session creation uses `idempotency_key`, webhook processing tracks `processed_events`. Safe to retry.

4. **Webhook-driven confirmation** — Bookings are confirmed by Stripe webhooks, not by polling or frontend callbacks. This is the most reliable pattern.

5. **Amounts in pence** — All monetary amounts are stored as integers in pence to avoid floating-point issues. Frontend converts to/from pounds for display.

6. **Callback URL pattern** — After processing a webhook, the payments module POSTs a simplified callback to `PAYMENTS_WEBHOOK_CALLBACK_URL`. This decouples the payments module from knowing how to update consumer models.

7. **Static frontend export** — The Next.js frontend is exported as static HTML/JS. No server-side rendering needed. Simple, fast, cheap to host.

---

## 14. Known Constraints

1. **Single callback URL** — `PAYMENTS_WEBHOOK_CALLBACK_URL` is a single URL. If multiple consumer apps need callbacks, implement a dispatcher or use `payable_type` routing.

2. **Single Gunicorn worker** — Railway hobby tier runs 1 worker. The internal function call pattern handles this. If scaling to multiple workers, HTTP calls between apps become safe again.

3. **No email sending** — The module doesn't send confirmation emails. Add this in the consumer app's webhook callback handler or use Stripe's built-in receipt emails.

4. **Test mode only** — Currently configured with Stripe test keys. Switch to live keys for production.

5. **No subscription support** — Currently handles one-time payments only. Stripe Subscriptions would need additional models and webhook handlers.

6. **Currency** — Defaults to GBP. Configurable via `DEFAULT_CURRENCY` env var, but multi-currency in a single deployment is not yet supported.
