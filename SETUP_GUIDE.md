# Quick Setup Guide

## Local Development Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
copy .env.example .env
```

Edit `.env` and add your Stripe keys:
- Get test keys from: https://dashboard.stripe.com/test/apikeys
- `STRIPE_SECRET_KEY`: starts with `sk_test_`
- `STRIPE_WEBHOOK_SECRET`: Get from Stripe CLI or webhook dashboard

### 4. Setup Database
```bash
# Create PostgreSQL database
createdb nbne_payments

# Run migrations
python manage.py makemigrations payments
python manage.py makemigrations bookings
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

### 6. Setup Stripe Webhooks (Local Testing)

Install Stripe CLI:
```bash
# Windows (with Scoop)
scoop install stripe

# Or download from: https://github.com/stripe/stripe-cli/releases
```

Forward webhooks to local server:
```bash
stripe login
stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/
```

Copy the webhook signing secret (starts with `whsec_`) to your `.env` file.

## Testing the Flow

### 1. Create a Booking with Payment
```bash
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "+44123456789",
    "service_name": "Premium Service",
    "booking_date": "2026-03-15T14:00:00Z",
    "total_amount_pence": 10000,
    "deposit_amount_pence": 5000
  }'
```

Response will include `checkout_url` - open this in browser to complete payment.

### 2. Test Webhook Events
```bash
# Trigger test events
stripe trigger checkout.session.completed
stripe trigger payment_intent.succeeded
```

### 3. Check Admin Panel
Visit http://localhost:8000/admin/ to view:
- Payment sessions
- Transactions
- Bookings
- Customers

### 4. Run Tests
```bash
python manage.py test payments
python manage.py test bookings
```

## Production Deployment (Railway)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: Django payments app"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. Deploy to Railway
1. Go to https://railway.app/
2. Create new project from GitHub repo
3. Add PostgreSQL plugin
4. Set environment variables (see Railway section in README.md)

### 3. Run Migrations on Railway
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

### 4. Configure Stripe Webhook
1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-app.railway.app/api/payments/webhook/stripe/`
3. Select events: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`
4. Copy signing secret to Railway environment variables

## Troubleshooting

### Database Connection Issues
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Ensure database exists: `psql -l`

### Stripe Webhook Not Working
- Check webhook secret is correct
- Verify Stripe CLI is running: `stripe listen`
- Check webhook endpoint is accessible
- View webhook logs in Stripe Dashboard

### Payment Not Completing
- Check Stripe test card: `4242 4242 4242 4242`
- Verify webhook events are being received
- Check Django logs for errors
- Ensure `PAYMENTS_ENABLED=True`

### Tests Failing
- Ensure test database can be created
- Check all dependencies installed
- Run migrations: `python manage.py migrate`

## API Testing with curl

### Create Checkout Session
```bash
curl -X POST http://localhost:8000/api/payments/checkout/ \
  -H "Content-Type: application/json" \
  -d '{
    "payable_type": "booking",
    "payable_id": "1",
    "amount_pence": 5000,
    "currency": "GBP",
    "customer": {
      "email": "test@example.com",
      "name": "Test User"
    },
    "success_url": "http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}",
    "cancel_url": "http://localhost:3000/cancel",
    "idempotency_key": "test-key-123"
  }'
```

### Check Payment Status
```bash
curl http://localhost:8000/api/payments/status/1/
```

### Get Booking
```bash
curl http://localhost:8000/api/bookings/1/
```

## Next Steps

1. **Frontend Integration**: Build React/Next.js frontend on Vercel
2. **Email Notifications**: Add booking confirmation emails
3. **Refund API**: Implement refund endpoint in payments app
4. **Reporting**: Add payment analytics dashboard
5. **Multi-tenancy**: Add organization/tenant support
6. **Additional Payment Methods**: Add Apple Pay, Google Pay support
