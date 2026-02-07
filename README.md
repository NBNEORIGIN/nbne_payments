# NBNE Payments — Reusable Django Payments Module

A generic, reusable Django payments module with Stripe Checkout integration. Designed as the payment backbone for a suite of business management apps (hair salons, fitness studios, restaurants, and more).

## Live Demo

| Component | URL |
|---|---|
| **Frontend** | https://nbne-payments-demo.netlify.app |
| **Backend API** | https://web-production-4e861.up.railway.app/api/ |
| **Django Admin** | https://web-production-4e861.up.railway.app/admin/ |

## Features

- **Generic Payable Linkage**: Works with any object type via `payable_type` + `payable_id` — no tight coupling
- **Stripe Checkout Integration**: Full Stripe Checkout Session creation and management
- **Webhook Handler**: Idempotent webhook processing with signature verification
- **Customer Management**: Automatic Stripe customer creation and linking
- **Transaction Ledger**: Complete payment and refund tracking
- **Internal Python API**: Consumer apps call functions directly (no HTTP self-calls, no deadlocks)
- **Django Admin**: Full admin interface with filters and reporting
- **Optional Payments**: Can be disabled per instance; bookings work without payments
- **Next.js Frontend**: Modern booking UI with shadcn/ui components

## Documentation

- **[MODULE_SPEC.md](MODULE_SPEC.md)** — Complete technical specification, data models, API reference, and integration guide
- **[AI_PROMPT_GUIDE.md](AI_PROMPT_GUIDE.md)** — Wiggum Loop prompts for AI-assisted development of new verticals (salon, fitness, restaurant, etc.)

## Project Structure

```
nbne-payments/
├── config/                     # Django project settings
│   ├── settings.py             # All settings, env vars, CORS, Stripe config
│   ├── urls.py                 # Root URL routing
│   └── wsgi.py                 # WSGI entry point
├── payments/                   # GENERIC PAYMENTS MODULE (reusable, do not modify per-vertical)
│   ├── models.py               # Customer, PaymentSession, Transaction, Refund
│   ├── views.py                # Checkout, webhook, status (internal + HTTP APIs)
│   ├── urls.py                 # /api/payments/ routes
│   ├── admin.py                # Django admin config
│   └── tests.py                # Unit tests
├── bookings/                   # REFERENCE CONSUMER APP (use as template for new verticals)
│   ├── models.py               # Booking model
│   ├── views.py                # Booking CRUD + payment integration
│   ├── urls.py                 # /api/bookings/ routes
│   └── tests.py                # Unit tests
├── frontend/                   # NEXT.JS FRONTEND
│   ├── src/app/                # Pages: landing, booking form, success, cancel, lookup
│   ├── src/lib/api.ts          # API client
│   └── netlify.toml            # Netlify deployment config
├── entrypoint.sh               # Railway startup (collectstatic, migrate, superuser, gunicorn)
├── Procfile                    # Railway process definition
├── requirements.txt            # Python dependencies
└── manage.py
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `STRIPE_SECRET_KEY`: Your Stripe secret key (sk_test_... or sk_live_...)
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook signing secret (whsec_...)
- `PAYMENTS_ENABLED`: Set to `True` to enable payments
- `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`: PostgreSQL connection details

Optional:
- `PAYMENTS_WEBHOOK_CALLBACK_URL`: URL to notify when payment status changes
- `DEFAULT_CURRENCY`: Default currency (default: GBP)

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Configure Stripe Webhook

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Forward webhooks to local server:
   ```bash
   stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/
   ```
3. Copy the webhook signing secret to your `.env` file as `STRIPE_WEBHOOK_SECRET`

For production, configure webhook endpoint in Stripe Dashboard:
- URL: `https://yourdomain.com/api/payments/webhook/stripe/`
- Events: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`

## API Endpoints

### Payments App

#### Create Checkout Session
```http
POST /api/payments/checkout/
Content-Type: application/json

{
  "payable_type": "booking",
  "payable_id": "18",
  "amount_pence": 1000,
  "currency": "GBP",
  "customer": {
    "email": "customer@example.com",
    "name": "John Doe",
    "phone": "+44123456789"
  },
  "success_url": "https://yoursite.com/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://yoursite.com/cancel",
  "metadata": {
    "service_name": "Premium Service",
    "deposit_pct": 50
  },
  "idempotency_key": "unique-key-123"
}
```

Response:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/...",
  "payment_session_id": "42",
  "status": "pending"
}
```

#### Get Payment Status
```http
GET /api/payments/status/{payment_session_id}/
```

Response:
```json
{
  "payment_session_id": "42",
  "payable_type": "booking",
  "payable_id": "18",
  "status": "succeeded",
  "amount_pence": 1000,
  "currency": "GBP"
}
```

#### Stripe Webhook
```http
POST /api/payments/webhook/stripe/
Stripe-Signature: ...
```

Handles events:
- `checkout.session.completed` → Updates status to `succeeded`, creates Transaction
- `checkout.session.expired` → Updates status to `canceled`
- `payment_intent.succeeded` → Updates status to `succeeded`
- `payment_intent.payment_failed` → Updates status to `failed`
- `charge.refunded` → Updates status to `refunded`, creates Refund

### Bookings App (Example Integration)

#### Create Booking
```http
POST /api/bookings/
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "customer_phone": "+44123456789",
  "service_name": "Premium Service",
  "booking_date": "2026-03-15T14:00:00Z",
  "total_amount_pence": 10000,
  "deposit_amount_pence": 5000,
  "notes": "Special requirements",
  "success_url": "https://yoursite.com/booking-success",
  "cancel_url": "https://yoursite.com/booking-cancel"
}
```

Response (with payment required):
```json
{
  "booking_id": 18,
  "status": "PENDING_PAYMENT",
  "checkout_url": "https://checkout.stripe.com/c/pay/...",
  "payment_session_id": "42"
}
```

#### Confirm Booking Payment
```http
POST /api/bookings/{booking_id}/confirm-payment/
Content-Type: application/json

{
  "payment_session_id": "42"
}
```

Response:
```json
{
  "booking_id": 18,
  "status": "CONFIRMED",
  "message": "Payment confirmed, booking is now confirmed"
}
```

## Data Models

### Customer
- `email` (unique): Customer email
- `name`: Customer name
- `phone`: Customer phone
- `provider`: Payment provider (default: "stripe")
- `provider_customer_id`: Stripe customer ID

### PaymentSession
- `payable_type`: Type of object being paid for (e.g., "booking", "order")
- `payable_id`: ID of the payable object
- `amount_pence`: Amount in pence/cents
- `currency`: Currency code (default: GBP)
- `status`: created | pending | succeeded | failed | canceled | refunded
- `stripe_checkout_session_id`: Stripe Checkout Session ID
- `stripe_payment_intent_id`: Stripe Payment Intent ID
- `customer`: FK to Customer
- `success_url`, `cancel_url`: Redirect URLs
- `metadata`: JSON field for additional data
- `idempotency_key`: Unique key to prevent duplicates
- `processed_events`: List of processed Stripe event IDs

### Transaction
- `payment_session`: FK to PaymentSession
- `gross_amount_pence`: Total amount charged
- `fee_amount_pence`: Payment processing fees (optional)
- `net_amount_pence`: Net amount after fees (optional)
- `currency`: Currency code
- `captured_at`: When payment was captured
- `provider_charge_id`: Stripe charge/payment intent ID

### Refund
- `transaction`: FK to Transaction
- `amount_pence`: Refund amount
- `reason`: Refund reason
- `status`: requested | succeeded | failed
- `provider_refund_id`: Stripe refund ID

## Integration Guide

### Adding Payments to Your App

The payments app is designed to be completely decoupled. To integrate:

1. **Create your payable object** (e.g., Booking, Order) with a status field
2. **When payment is required**:
   - Create your object in a "pending payment" state
   - Call `/api/payments/checkout/` with `payable_type` and `payable_id`
   - Redirect user to the returned `checkout_url`
3. **Handle payment completion**:
   - Option A: Poll `/api/payments/status/{payment_session_id}/` after user returns
   - Option B: Set `PAYMENTS_WEBHOOK_CALLBACK_URL` to receive automatic notifications
4. **Update your object** when payment succeeds/fails

### Webhook Callback (Optional)

Set `PAYMENTS_WEBHOOK_CALLBACK_URL` in settings. When a payment status changes, payments app will POST:

```json
{
  "payable_type": "booking",
  "payable_id": "18",
  "payment_session_id": "42",
  "status": "succeeded"
}
```

Your app can handle this to automatically update booking status.

## Security

- ✅ Webhook signature verification (Stripe-Signature header)
- ✅ Idempotent event processing (prevents duplicate processing)
- ✅ Amount validation (server-side only, never trust frontend)
- ✅ CSRF protection on non-webhook endpoints
- ✅ Unique idempotency keys prevent duplicate charges

## Testing

Run tests:
```bash
python manage.py test payments
python manage.py test bookings
```

Test webhook locally with Stripe CLI:
```bash
stripe trigger checkout.session.completed
```

## Deployment (Railway)

### Environment Variables

Set in Railway dashboard:
- `DJANGO_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `PAYMENTS_ENABLED=True`
- `ALLOWED_HOSTS=yourdomain.railway.app`
- `CSRF_TRUSTED_ORIGINS=https://yourdomain.railway.app,https://yourfrontend.vercel.app`
- Database variables (auto-configured by Railway PostgreSQL plugin)

### Deployment Steps

1. Connect Railway to your GitHub repo
2. Add PostgreSQL plugin
3. Set environment variables
4. Deploy: `railway up`
5. Run migrations: `railway run python manage.py migrate`
6. Create superuser: `railway run python manage.py createsuperuser`
7. Configure Stripe webhook URL in Stripe Dashboard

## Admin Interface

Access at `/admin/` after creating a superuser.

Features:
- View all payment sessions with filters by status, type, date
- View transactions and refunds
- Search by customer email, payment IDs
- View detailed payment metadata

## Disabling Payments

Set `PAYMENTS_ENABLED=False` in environment. Bookings will be created directly in CONFIRMED status without payment flow.

## Currency Support

Default currency is GBP. To change:
- Set `DEFAULT_CURRENCY` environment variable
- Pass `currency` parameter in checkout API calls
- Amounts are always in smallest currency unit (pence for GBP, cents for USD, etc.)

## License

MIT
