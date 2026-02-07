"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Search, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { getBooking, formatPence, type BookingDetails } from "@/lib/api";

function statusColor(status: string) {
  switch (status) {
    case "CONFIRMED":
      return "default";
    case "PENDING_PAYMENT":
      return "secondary";
    case "CANCELLED":
      return "destructive";
    default:
      return "outline";
  }
}

export default function BookingLookupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    }>
      <BookingLookupContent />
    </Suspense>
  );
}

function BookingLookupContent() {
  const searchParams = useSearchParams();
  const [bookingId, setBookingId] = useState(searchParams.get("id") || "");
  const [booking, setBooking] = useState<BookingDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLookup = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!bookingId) return;

    setLoading(true);
    setError("");
    setBooking(null);

    try {
      const data = await getBooking(parseInt(bookingId));
      setBooking(data);
    } catch {
      setError("Booking not found. Please check the ID and try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (searchParams.get("id")) {
      handleLookup();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>
          </Link>
          <h1 className="text-xl font-bold tracking-tight">NBNE Signs</h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-12 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Check Booking Status</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLookup} className="flex gap-3">
              <div className="flex-1 space-y-2">
                <Label htmlFor="booking-id" className="sr-only">
                  Booking ID
                </Label>
                <Input
                  id="booking-id"
                  type="number"
                  min="1"
                  placeholder="Enter booking ID..."
                  value={bookingId}
                  onChange={(e) => setBookingId(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" disabled={loading || !bookingId}>
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 text-sm text-center">
            {error}
          </div>
        )}

        {booking && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">
                Booking #{booking.booking_id}
              </CardTitle>
              <Badge variant={statusColor(booking.status)}>
                {booking.status}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Customer</span>
                  <span>{booking.customer_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Email</span>
                  <span>{booking.customer_email}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Service</span>
                  <span>{booking.service_name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Date</span>
                  <span>
                    {new Date(booking.booking_date).toLocaleDateString("en-GB", {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total</span>
                  <span>{formatPence(booking.total_amount_pence)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Deposit</span>
                  <span>{formatPence(booking.deposit_amount_pence)}</span>
                </div>
                {booking.deposit_amount_pence > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Remaining</span>
                    <span>
                      {formatPence(
                        booking.total_amount_pence - booking.deposit_amount_pence
                      )}
                    </span>
                  </div>
                )}
                {booking.notes && (
                  <div className="pt-2 border-t">
                    <span className="text-sm text-muted-foreground">Notes</span>
                    <p className="text-sm mt-1">{booking.notes}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
