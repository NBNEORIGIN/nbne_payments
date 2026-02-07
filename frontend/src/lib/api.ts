const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface BookingRequest {
  customer_name: string;
  customer_email: string;
  customer_phone?: string;
  service_name: string;
  booking_date: string;
  total_amount_pence: number;
  deposit_amount_pence: number;
  notes?: string;
  success_url?: string;
  cancel_url?: string;
}

export interface BookingResponse {
  booking_id: number;
  status: string;
  checkout_url?: string;
  payment_session_id?: string;
  message?: string;
}

export interface BookingDetails {
  booking_id: number;
  customer_name: string;
  customer_email: string;
  service_name: string;
  booking_date: string;
  total_amount_pence: number;
  deposit_amount_pence: number;
  status: string;
  notes: string;
}

export async function createBooking(data: BookingRequest): Promise<BookingResponse> {
  const res = await fetch(`${API_URL}/api/bookings/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.error || 'Failed to create booking');
  }

  return json;
}

export async function getBooking(bookingId: number): Promise<BookingDetails> {
  const res = await fetch(`${API_URL}/api/bookings/${bookingId}/`);
  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.error || 'Failed to fetch booking');
  }

  return json;
}

export async function confirmBookingPayment(
  bookingId: number,
  paymentSessionId: string
): Promise<BookingResponse> {
  const res = await fetch(`${API_URL}/api/bookings/${bookingId}/confirm-payment/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payment_session_id: paymentSessionId }),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.error || 'Failed to confirm payment');
  }

  return json;
}

export function formatPence(pence: number): string {
  return `£${(pence / 100).toFixed(2)}`;
}
