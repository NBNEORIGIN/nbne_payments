"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getBooking, formatPence, type BookingDetails } from "@/lib/api";

export default function BookingSuccessPage() {
  const [booking, setBooking] = useState<BookingDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const bookingId = sessionStorage.getItem("nbne_booking_id");

    if (!bookingId) {
      setError("No booking found. Please check your email for confirmation.");
      setLoading(false);
      return;
    }

    const fetchBooking = async () => {
      try {
        const data = await getBooking(parseInt(bookingId));
        setBooking(data);
      } catch {
        setError("Could not load booking details.");
      } finally {
        setLoading(false);
      }
    };

    // Small delay to allow webhook to process
    const timer = setTimeout(fetchBooking, 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <h1 className="text-xl font-bold tracking-tight">NBNE Signs</h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-16">
        {loading ? (
          <div className="text-center space-y-4">
            <Loader2 className="w-12 h-12 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Confirming your payment...</p>
          </div>
        ) : error ? (
          <Card>
            <CardContent className="pt-8 text-center space-y-4">
              <p className="text-muted-foreground">{error}</p>
              <Link href="/">
                <Button>Return Home</Button>
              </Link>
            </CardContent>
          </Card>
        ) : booking ? (
          <Card>
            <CardHeader className="text-center space-y-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <CardTitle className="text-2xl">
                {booking.status === "CONFIRMED"
                  ? "Booking Confirmed!"
                  : "Payment Received!"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-slate-50 rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Booking ID</span>
                  <span className="font-mono">#{booking.booking_id}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Service</span>
                  <span>{booking.service_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Date</span>
                  <span>{new Date(booking.booking_date).toLocaleDateString("en-GB", {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Deposit Paid</span>
                  <span className="font-semibold text-green-600">
                    {formatPence(booking.deposit_amount_pence)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Remaining Balance</span>
                  <span>
                    {formatPence(booking.total_amount_pence - booking.deposit_amount_pence)}
                  </span>
                </div>
                <div className="flex justify-between text-sm items-center">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={booking.status === "CONFIRMED" ? "default" : "secondary"}>
                    {booking.status}
                  </Badge>
                </div>
              </div>

              <p className="text-sm text-muted-foreground text-center">
                A confirmation email will be sent to <strong>{booking.customer_email}</strong>.
              </p>

              <div className="flex gap-3 pt-2">
                <Link href="/" className="flex-1">
                  <Button variant="outline" className="w-full">Return Home</Button>
                </Link>
                <Link href={`/booking/lookup?id=${booking.booking_id}`} className="flex-1">
                  <Button className="w-full">View Booking</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : null}
      </main>
    </div>
  );
}
