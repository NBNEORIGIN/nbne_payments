# AI Prompt Guide — Wiggum Loop Prompts for NBNE Business Management Suite

## What This Document Is

This guide contains a series of structured AI prompts designed to be fed into an AI coding assistant (Windsurf Cascade, Cursor, etc.) to systematically build out the NBNE business management suite. Each prompt is a self-contained "Wiggum Loop" — a prompt that gives the AI enough context to produce a complete, working feature in one pass.

**Prerequisites:** The AI must have access to the `nbne-payments` repository and should read `MODULE_SPEC.md` before starting any vertical.

---

## Table of Contents

1. [Context Primer Prompt](#1-context-primer-prompt)
2. [Hair Salon Appointments](#2-hair-salon-appointments)
3. [Fitness Studio Classes](#3-fitness-studio-classes)
4. [Restaurant Reservations](#4-restaurant-reservations)
5. [Multi-Vertical Webhook Dispatcher](#5-multi-vertical-webhook-dispatcher)
6. [Shared Frontend Shell](#6-shared-frontend-shell)
7. [Hair Salon Frontend](#7-hair-salon-frontend)
8. [Fitness Studio Frontend](#8-fitness-studio-frontend)
9. [Restaurant Frontend](#9-restaurant-frontend)
10. [Admin Dashboard](#10-admin-dashboard)
11. [Email Notifications](#11-email-notifications)
12. [Go Live Checklist](#12-go-live-checklist)

---

## 1. Context Primer Prompt

> **Use this prompt at the start of every new session to give the AI full context.**

```
Read the file MODULE_SPEC.md in the project root. This is the complete technical specification
for the NBNE Payments Module — a generic, reusable Django payments app with Stripe Checkout
integration.

Key facts:
- The payments app is at `payments/` and must NEVER be modified for vertical-specific logic.
- The bookings app at `bookings/` is a REFERENCE IMPLEMENTATION showing how to integrate.
- New verticals call `create_checkout_session_internal()` from `payments.views` directly
  (never via HTTP) to avoid single-worker deadlocks.
- All amounts are in pence (integers). £50.00 = 5000.
- The payments module uses `payable_type` (string) and `payable_id` (string) to generically
  link to any model.
- Stripe webhooks auto-confirm payments. Consumer apps receive callbacks at their
  `webhook/payment/` endpoint.
- Backend is Django 4.2 on Railway with PostgreSQL.
- Frontend is Next.js 16 with TypeScript, TailwindCSS, shadcn/ui on Netlify.
- CORS is configured via `CORS_ALLOWED_ORIGINS` env var.

The existing codebase has:
- `config/` — Django project settings, urls, wsgi
- `payments/` — Generic payments module (DO NOT MODIFY)
- `bookings/` — Reference consumer app (use as template)
- `frontend/` — Next.js demo frontend (use as template)
- `entrypoint.sh` — Railway startup script
- `requirements.txt` — Python dependencies

Study the bookings app (models.py, views.py, urls.py) as the pattern to follow.
```

---

## 2. Hair Salon Appointments

```
TASK: Create a Django app called `salon` for hair salon appointment booking with payment integration.

CONTEXT: Read MODULE_SPEC.md first. Use the `bookings` app as your template. The `payments`
module is already built — call its internal functions, do NOT modify it.

REQUIREMENTS:

1. Create `salon/models.py` with an `Appointment` model:
   - client_name (CharField, max 255)
   - client_email (EmailField)
   - client_phone (CharField, max 50, blank)
   - stylist_name (CharField, max 255)
   - service_name (CharField, max 255)
   - appointment_datetime (DateTimeField)
   - duration_minutes (IntegerField, default 60)
   - price_pence (IntegerField)
   - deposit_pence (IntegerField, default 0)
   - status (CharField: PENDING_PAYMENT, CONFIRMED, CANCELLED, COMPLETED, NO_SHOW)
   - notes (TextField, blank)
   - created_at, updated_at (auto)

2. Create `salon/views.py` with these endpoints:
   - POST /api/salon/appointments/ — create appointment, call create_checkout_session_internal()
     if deposit > 0, return checkout_url. Use payable_type='salon_appointment'.
   - GET /api/salon/appointments/<id>/ — get appointment details
   - POST /api/salon/appointments/<id>/confirm-payment/ — manually confirm via
     get_payment_status_internal()
   - POST /api/salon/webhook/payment/ — receive payment callbacks, update appointment status
   - GET /api/salon/stylists/ — return hardcoded list of stylists with their services and prices
     (we'll make this dynamic later)

3. Create `salon/urls.py` with the URL patterns.

4. Create `salon/admin.py` with admin registration.

5. Create `salon/tests.py` with tests following the same pattern as bookings/tests.py.
   Mock create_checkout_session_internal and get_payment_status_internal.

6. Add 'salon' to INSTALLED_APPS in config/settings.py.

7. Add path('api/salon/', include('salon.urls')) to config/urls.py.

8. Run makemigrations and migrate.

9. Run tests to verify everything passes.

HARDCODED STYLISTS DATA (for the /api/salon/stylists/ endpoint):
[
  {
    "name": "Sarah Johnson",
    "services": [
      {"name": "Women's Cut & Blow Dry", "duration": 60, "price_pence": 4500},
      {"name": "Women's Cut, Colour & Blow Dry", "duration": 120, "price_pence": 9500},
      {"name": "Blow Dry", "duration": 30, "price_pence": 2500},
      {"name": "Hair Up / Occasion", "duration": 60, "price_pence": 5500}
    ]
  },
  {
    "name": "Mike Chen",
    "services": [
      {"name": "Men's Cut", "duration": 30, "price_pence": 2500},
      {"name": "Men's Cut & Beard Trim", "duration": 45, "price_pence": 3500},
      {"name": "Buzz Cut", "duration": 15, "price_pence": 1500}
    ]
  },
  {
    "name": "Emma Williams",
    "services": [
      {"name": "Full Head Colour", "duration": 90, "price_pence": 8500},
      {"name": "Half Head Highlights", "duration": 90, "price_pence": 7500},
      {"name": "Full Head Highlights", "duration": 120, "price_pence": 10500},
      {"name": "Balayage", "duration": 150, "price_pence": 12500},
      {"name": "Toner / Gloss", "duration": 30, "price_pence": 3000}
    ]
  }
]

DEPOSIT RULE: 50% deposit required for all services over £30.00 (3000 pence).

IMPORTANT:
- Import from payments.views: create_checkout_session_internal, get_payment_status_internal
- Use payable_type='salon_appointment' in all payment calls
- Follow the EXACT same patterns as bookings/views.py
- All amounts in pence
- Do NOT modify the payments app
```

---

## 3. Fitness Studio Classes

```
TASK: Create a Django app called `fitness` for fitness studio class booking with payment integration.

CONTEXT: Read MODULE_SPEC.md first. Use the `bookings` app as your template. The `payments`
module is already built — call its internal functions, do NOT modify it.

REQUIREMENTS:

1. Create `fitness/models.py` with these models:

   FitnessClass:
   - name (CharField, max 255) — e.g. "Spin", "Yoga", "HIIT"
   - instructor_name (CharField, max 255)
   - description (TextField, blank)
   - datetime (DateTimeField)
   - duration_minutes (IntegerField, default 45)
   - max_capacity (IntegerField, default 20)
   - price_pence (IntegerField)
   - location (CharField, max 255, default "Studio 1")
   - status (CharField: SCHEDULED, CANCELLED, COMPLETED)
   - created_at, updated_at (auto)
   
   ClassBooking:
   - fitness_class (ForeignKey → FitnessClass)
   - client_name (CharField, max 255)
   - client_email (EmailField)
   - client_phone (CharField, max 50, blank)
   - status (CharField: PENDING_PAYMENT, CONFIRMED, CANCELLED, NO_SHOW)
   - notes (TextField, blank)
   - created_at, updated_at (auto)
   
   Add a property `spots_remaining` on FitnessClass that returns max_capacity minus
   confirmed bookings count.

2. Create `fitness/views.py` with these endpoints:
   - GET /api/fitness/classes/ — list upcoming classes with spots_remaining
   - GET /api/fitness/classes/<id>/ — get class details with bookings count
   - POST /api/fitness/classes/<id>/book/ — book a spot. If price > 0, call
     create_checkout_session_internal() with payable_type='class_booking'.
     Check capacity before booking. Return checkout_url.
   - GET /api/fitness/bookings/<id>/ — get booking details
   - POST /api/fitness/webhook/payment/ — receive payment callbacks

3. Create urls.py, admin.py, tests.py following the bookings pattern.

4. Register in settings and urls.

5. Run makemigrations, migrate, tests.

CAPACITY RULE: Reject bookings if spots_remaining <= 0.
PAYMENT RULE: Full payment upfront (no deposit — charge the full class price).
PAYABLE_TYPE: 'class_booking'

IMPORTANT:
- Import from payments.views: create_checkout_session_internal, get_payment_status_internal
- Follow the EXACT same patterns as bookings/views.py
- Do NOT modify the payments app
```

---

## 4. Restaurant Reservations

```
TASK: Create a Django app called `restaurant` for restaurant table reservation with optional
deposit payment integration.

CONTEXT: Read MODULE_SPEC.md first. Use the `bookings` app as your template. The `payments`
module is already built — call its internal functions, do NOT modify it.

REQUIREMENTS:

1. Create `restaurant/models.py` with these models:

   Table:
   - number (IntegerField, unique)
   - capacity (IntegerField) — max guests
   - location (CharField: INDOOR, OUTDOOR, BAR, PRIVATE)
   - is_active (BooleanField, default True)
   
   Reservation:
   - table (ForeignKey → Table, nullable — assigned later)
   - guest_name (CharField, max 255)
   - guest_email (EmailField)
   - guest_phone (CharField, max 50)
   - party_size (IntegerField)
   - reservation_datetime (DateTimeField)
   - duration_minutes (IntegerField, default 90)
   - deposit_pence (IntegerField, default 0)
   - status (CharField: PENDING_PAYMENT, CONFIRMED, SEATED, COMPLETED, CANCELLED, NO_SHOW)
   - special_requests (TextField, blank)
   - created_at, updated_at (auto)

2. Create `restaurant/views.py` with these endpoints:
   - GET /api/restaurant/availability/?date=2026-03-15&party_size=4&time=19:00
     — check available time slots. Return available 30-min slots between 12:00-22:00
     where a table with sufficient capacity is free.
   - POST /api/restaurant/reservations/ — create reservation. If deposit > 0, call
     create_checkout_session_internal() with payable_type='restaurant_reservation'.
   - GET /api/restaurant/reservations/<id>/ — get reservation details
   - POST /api/restaurant/webhook/payment/ — receive payment callbacks

3. Create urls.py, admin.py, tests.py.

4. Register in settings and urls.

5. Run makemigrations, migrate, tests.

DEPOSIT RULE: £10.00 (1000 pence) deposit per person for parties of 6+. No deposit for
smaller parties (they are confirmed immediately).
PAYABLE_TYPE: 'restaurant_reservation'
AVAILABILITY: A table is "available" for a time slot if no confirmed/seated reservation
overlaps that slot (considering duration_minutes).

IMPORTANT:
- Import from payments.views: create_checkout_session_internal, get_payment_status_internal
- Follow the EXACT same patterns as bookings/views.py
- Do NOT modify the payments app
```

---

## 5. Multi-Vertical Webhook Dispatcher

```
TASK: Refactor the webhook callback system to support multiple consumer apps.

CONTEXT: Read MODULE_SPEC.md. Currently PAYMENTS_WEBHOOK_CALLBACK_URL is a single URL.
With multiple verticals (bookings, salon, fitness, restaurant), we need to route callbacks
to the correct app based on payable_type.

REQUIREMENTS:

1. Create a new file `config/webhook_dispatcher.py` with a view that:
   - Receives POST from the payments module callback
   - Reads `payable_type` from the JSON body
   - Routes to the correct consumer app's webhook handler based on a mapping:
     ```python
     CALLBACK_ROUTES = {
         'booking': '/api/bookings/webhook/payment/',
         'salon_appointment': '/api/salon/webhook/payment/',
         'class_booking': '/api/fitness/webhook/payment/',
         'restaurant_reservation': '/api/restaurant/webhook/payment/',
     }
     ```
   - Makes an internal function call (NOT HTTP) to the correct handler
   - Returns the handler's response

2. Register the dispatcher at `/api/webhooks/payment-callback/` in config/urls.py.

3. Update the Railway env var instructions:
   PAYMENTS_WEBHOOK_CALLBACK_URL should point to the dispatcher:
   https://web-production-4e861.up.railway.app/api/webhooks/payment-callback/

IMPORTANT:
- The dispatcher must call consumer handlers as Python functions, not HTTP requests
- Each consumer's payment_webhook_callback view should be importable and callable
- Do NOT modify the payments app
- Add tests for the dispatcher
```

---

## 6. Shared Frontend Shell

```
TASK: Refactor the Next.js frontend into a multi-vertical app shell with shared layout
and navigation.

CONTEXT: The current frontend at `frontend/` is a single-purpose booking demo. We need to
turn it into a shared shell that can host multiple verticals.

REQUIREMENTS:

1. Update `src/app/layout.tsx` to include a responsive navigation bar with:
   - NBNE logo/brand on the left
   - Navigation links: Home, Hair Salon, Fitness, Restaurant
   - Mobile hamburger menu

2. Update `src/app/page.tsx` to be a dashboard/landing showing cards for each vertical:
   - Hair Salon — "Book an appointment with our stylists"
   - Fitness Studio — "Book a class"
   - Restaurant — "Reserve a table"
   - Each card links to its vertical's booking page

3. Create shared components:
   - `src/components/layout/navbar.tsx` — responsive nav
   - `src/components/layout/footer.tsx` — shared footer
   - `src/components/shared/payment-status-badge.tsx` — reusable status badge
   - `src/components/shared/price-display.tsx` — formats pence to £

4. Update `src/lib/api.ts` to add API functions for all verticals:
   - Salon: createAppointment, getAppointment, getStylists
   - Fitness: getClasses, bookClass, getClassBooking
   - Restaurant: checkAvailability, createReservation, getReservation

5. Keep the existing booking pages working under /booking/*

TECH STACK: Next.js 16, TypeScript, TailwindCSS, shadcn/ui, Lucide icons.
Use static export (output: "export" in next.config.ts).

IMPORTANT:
- All API calls go to NEXT_PUBLIC_API_URL
- Use shadcn/ui components consistently
- Mobile-first responsive design
- Keep the existing booking pages working
```

---

## 7. Hair Salon Frontend

```
TASK: Build the hair salon appointment booking frontend pages.

CONTEXT: The shared frontend shell is at `frontend/`. The salon backend API is at
/api/salon/. Read MODULE_SPEC.md for the payments flow.

REQUIREMENTS:

1. Create `src/app/salon/page.tsx` — salon landing page:
   - Hero section with salon branding
   - "Book Appointment" CTA button
   - Display stylists with their photos (placeholder) and specialties

2. Create `src/app/salon/book/page.tsx` — appointment booking form:
   - Step 1: Select stylist (fetch from /api/salon/stylists/)
   - Step 2: Select service (filtered by chosen stylist)
   - Step 3: Select date and time (date picker + time slot grid)
   - Step 4: Enter client details (name, email, phone)
   - Step 5: Review & pay — show summary, deposit amount, "Pay Deposit" button
   - On submit: POST to /api/salon/appointments/, redirect to Stripe Checkout
   - Store appointment_id in sessionStorage

3. Create `src/app/salon/success/page.tsx` — appointment confirmed:
   - Show green checkmark, appointment details
   - Stylist name, service, date/time, deposit paid, remaining balance

4. Create `src/app/salon/cancel/page.tsx` — payment cancelled

5. Create `src/app/salon/lookup/page.tsx` — check appointment status by ID

DESIGN: Modern, clean salon aesthetic. Use a warm colour palette.
Ensure mobile-first responsive design — most salon bookings happen on phones.

IMPORTANT:
- Use the API functions from src/lib/api.ts
- Follow the same patterns as the existing booking pages
- All amounts in pence, display as £
- Use shadcn/ui components
```

---

## 8. Fitness Studio Frontend

```
TASK: Build the fitness studio class booking frontend pages.

CONTEXT: The shared frontend shell is at `frontend/`. The fitness backend API is at
/api/fitness/. Read MODULE_SPEC.md for the payments flow.

REQUIREMENTS:

1. Create `src/app/fitness/page.tsx` — class schedule page:
   - Weekly timetable/grid view showing upcoming classes
   - Each class card shows: name, instructor, time, duration, spots remaining, price
   - Filter by: day of week, class type, instructor
   - "Book" button on each class (disabled if full)

2. Create `src/app/fitness/book/[classId]/page.tsx` — book a specific class:
   - Show class details (name, instructor, datetime, price, spots left)
   - Client details form (name, email, phone)
   - "Pay & Book" button — full payment upfront
   - On submit: POST to /api/fitness/classes/<id>/book/, redirect to Stripe Checkout

3. Create `src/app/fitness/success/page.tsx` — booking confirmed:
   - Show class details, confirmation

4. Create `src/app/fitness/cancel/page.tsx` — payment cancelled

5. Create `src/app/fitness/lookup/page.tsx` — check booking status

DESIGN: Energetic, bold fitness aesthetic. Use strong colours and dynamic layout.
Show capacity as a progress bar (e.g. "3 spots left out of 20").

IMPORTANT:
- Fetch class list from /api/fitness/classes/
- Handle "class full" state gracefully
- Use the API functions from src/lib/api.ts
- All amounts in pence, display as £
- Use shadcn/ui components
```

---

## 9. Restaurant Frontend

```
TASK: Build the restaurant reservation frontend pages.

CONTEXT: The shared frontend shell is at `frontend/`. The restaurant backend API is at
/api/restaurant/. Read MODULE_SPEC.md for the payments flow.

REQUIREMENTS:

1. Create `src/app/restaurant/page.tsx` — restaurant landing:
   - Hero with restaurant imagery (placeholder)
   - "Reserve a Table" CTA
   - Opening hours, location info

2. Create `src/app/restaurant/reserve/page.tsx` — reservation form:
   - Step 1: Select date (date picker, future dates only)
   - Step 2: Select party size (1-12 dropdown)
   - Step 3: Select time slot (fetch from /api/restaurant/availability/?date=X&party_size=Y)
     — show available slots as a grid of buttons
   - Step 4: Guest details (name, email, phone, special requests textarea)
   - Step 5: Review — show summary. If party >= 6, show deposit amount (£10/person).
     If party < 6, show "No deposit required".
   - On submit: POST to /api/restaurant/reservations/
     — If deposit required, redirect to Stripe Checkout
     — If no deposit, show confirmation directly

3. Create `src/app/restaurant/success/page.tsx` — reservation confirmed

4. Create `src/app/restaurant/cancel/page.tsx` — payment cancelled

5. Create `src/app/restaurant/lookup/page.tsx` — check reservation status

DESIGN: Elegant, sophisticated restaurant aesthetic. Dark theme option.
Show available time slots clearly — grey out unavailable ones.

IMPORTANT:
- Availability check is async — show loading state
- Handle "no availability" gracefully
- Deposit only for parties of 6+ (£10/person)
- Use the API functions from src/lib/api.ts
- All amounts in pence, display as £
- Use shadcn/ui components
```

---

## 10. Admin Dashboard

```
TASK: Build a custom admin dashboard frontend for business owners to manage all verticals.

CONTEXT: The Django admin at /admin/ works but is generic. Build a custom dashboard that
gives business owners a unified view across all verticals.

REQUIREMENTS:

1. Create `src/app/admin/page.tsx` — dashboard overview:
   - Today's summary cards: total bookings, revenue, upcoming appointments
   - Cards per vertical: Salon appointments today, Fitness classes today, Restaurant covers today
   - Recent activity feed (latest 10 bookings across all verticals)

2. Create `src/app/admin/salon/page.tsx` — salon management:
   - Today's appointment list with status badges
   - Quick actions: mark as completed, mark as no-show, cancel
   - Revenue summary for the day/week/month

3. Create `src/app/admin/fitness/page.tsx` — fitness management:
   - Today's class schedule with booking counts
   - Capacity utilisation per class
   - Quick actions: cancel class

4. Create `src/app/admin/restaurant/page.tsx` — restaurant management:
   - Today's reservation list with table assignments
   - Timeline view of table occupancy
   - Quick actions: seat, complete, no-show

5. Create `src/app/admin/payments/page.tsx` — payments overview:
   - Recent transactions across all verticals
   - Revenue by vertical (bar chart)
   - Payment status breakdown (pie chart)

BACKEND: You'll need to add new API endpoints for aggregated data:
- GET /api/admin/dashboard/ — summary stats
- GET /api/admin/revenue/?period=week — revenue data
These should be in a new `dashboard` Django app.

DESIGN: Clean, data-dense dashboard. Use shadcn/ui cards, tables, and badges.
Consider using recharts or similar for charts.

IMPORTANT:
- This is an internal tool — no public access needed
- Add basic auth check (API key header or session auth)
- Mobile-responsive but optimised for desktop
```

---

## 11. Email Notifications

```
TASK: Add email notification support to all verticals.

CONTEXT: Currently no emails are sent. Add transactional emails for key events.

REQUIREMENTS:

1. Create a `notifications` Django app with:
   - A reusable `send_email(to, subject, template_name, context)` function
   - HTML email templates using Django's template engine
   - Support for SendGrid, Mailgun, or Django's SMTP backend (configurable via env vars)

2. Email templates needed:
   - `booking_confirmed.html` — booking/appointment/reservation confirmed
   - `payment_received.html` — payment receipt
   - `booking_cancelled.html` — booking cancelled
   - `booking_reminder.html` — reminder 24h before (for future cron job)

3. Integration points — add email sending to each vertical's webhook callback handler:
   - On payment succeeded → send booking_confirmed + payment_received
   - On payment failed/cancelled → send booking_cancelled

4. Environment variables:
   - EMAIL_BACKEND (smtp/sendgrid/mailgun)
   - EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
   - DEFAULT_FROM_EMAIL

IMPORTANT:
- Emails must not block the webhook response — use Django's send_mail (it's fast enough
  for transactional email) or queue with a simple threading approach
- Templates should be branded and mobile-responsive HTML
- Include plain text alternatives
- Do NOT modify the payments app
```

---

## 12. Go Live Checklist

```
TASK: Prepare the entire suite for production launch.

CONTEXT: Everything is currently running on Stripe test mode with test keys.

REQUIREMENTS:

1. Stripe:
   - Switch to live Stripe keys (sk_live_..., whsec_...)
   - Create production webhook endpoint in Stripe Dashboard (live mode)
   - Update Railway env vars: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

2. Security:
   - Set DEBUG=False on Railway
   - Generate new DJANGO_SECRET_KEY for production
   - Audit ALLOWED_HOSTS — remove '*', set specific domains
   - Audit CORS_ALLOWED_ORIGINS — only allow production frontend domain
   - Add rate limiting to API endpoints (django-ratelimit)
   - Add HTTPS redirect middleware

3. Database:
   - Ensure Railway PostgreSQL has backups enabled
   - Run a test migration on production

4. Frontend:
   - Update NEXT_PUBLIC_API_URL to production backend
   - Remove any test/demo data references
   - Add proper error pages (404, 500)
   - Add favicon and Open Graph meta tags

5. Monitoring:
   - Add Sentry for error tracking (both Django and Next.js)
   - Add health check endpoint: GET /api/health/ → {"status": "ok"}
   - Set up uptime monitoring (UptimeRobot or similar)

6. Documentation:
   - Update README.md with production URLs
   - Document the deployment process
   - Create runbook for common operations (refunds, cancellations, etc.)

OUTPUT: A checklist document with each item, its status, and instructions.
```

---

## Prompt Sequencing Guide

### Recommended order for building out the suite:

```
Phase 1 — Backend Verticals (do these first, in any order)
  → Prompt 1 (Context Primer) — always run first
  → Prompt 2 (Hair Salon)
  → Prompt 3 (Fitness Studio)
  → Prompt 4 (Restaurant)
  → Prompt 5 (Webhook Dispatcher)

Phase 2 — Frontend
  → Prompt 1 (Context Primer)
  → Prompt 6 (Shared Shell)
  → Prompt 7 (Salon Frontend)
  → Prompt 8 (Fitness Frontend)
  → Prompt 9 (Restaurant Frontend)

Phase 3 — Polish
  → Prompt 10 (Admin Dashboard)
  → Prompt 11 (Email Notifications)
  → Prompt 12 (Go Live Checklist)
```

### Tips for best results:

1. **Always start with the Context Primer** (Prompt 1) in a new session
2. **One prompt per session** — don't combine prompts
3. **Test after each prompt** — run `python manage.py test` and fix issues before moving on
4. **Commit after each prompt** — `git add -A && git commit -m "Add [vertical] app"`
5. **Deploy after each backend prompt** — push to GitHub, Railway auto-deploys
6. **Deploy frontend separately** — `netlify deploy --prod` from `frontend/`

### Adapting prompts for other verticals:

To add a new vertical (e.g. "spa treatments", "pet grooming", "tutoring"):

1. Copy the closest existing prompt (salon, fitness, or restaurant)
2. Change the model fields to match the new domain
3. Change `payable_type` to a unique string (e.g. `'spa_treatment'`)
4. Add the new type to the webhook dispatcher mapping
5. Create frontend pages following the same pattern
