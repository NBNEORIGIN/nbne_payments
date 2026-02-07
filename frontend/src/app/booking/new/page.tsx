"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { createBooking, formatPence } from "@/lib/api";

const SERVICES = [
  { name: "Shop Front Signage", price: 45000 },
  { name: "Vehicle Graphics", price: 25000 },
  { name: "Banner & Display", price: 15000 },
  { name: "Window Graphics", price: 20000 },
  { name: "Custom Project", price: 0 },
];

export default function NewBookingPage() {
  const [formData, setFormData] = useState({
    customer_name: "",
    customer_email: "",
    customer_phone: "",
    service_name: "",
    booking_date: "",
    total_amount_pence: 0,
    deposit_amount_pence: 0,
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleServiceChange = (serviceName: string) => {
    const service = SERVICES.find((s) => s.name === serviceName);
    const total = service?.price || 0;
    const deposit = Math.round(total * 0.5);
    setFormData((prev) => ({
      ...prev,
      service_name: serviceName,
      total_amount_pence: total,
      deposit_amount_pence: deposit,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const origin = window.location.origin;
      const result = await createBooking({
        ...formData,
        success_url: `${origin}/booking/success?session_id={CHECKOUT_SESSION_ID}&booking_id=${0}`,
        cancel_url: `${origin}/booking/cancel`,
      });

      if (result.checkout_url) {
        // Store booking ID for the success page
        sessionStorage.setItem("nbne_booking_id", String(result.booking_id));
        sessionStorage.setItem("nbne_payment_session_id", String(result.payment_session_id));
        window.location.href = result.checkout_url;
      } else {
        // No payment needed, booking confirmed directly
        window.location.href = `${origin}/booking/success?booking_id=${result.booking_id}`;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const isCustom = formData.service_name === "Custom Project";

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

      <main className="max-w-2xl mx-auto px-4 py-12">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">New Booking</CardTitle>
            <CardDescription>
              Fill in your details and select a service. A 50% deposit is required to confirm your booking.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <h3 className="font-semibold">Your Details</h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name *</Label>
                    <Input
                      id="name"
                      required
                      value={formData.customer_name}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, customer_name: e.target.value }))
                      }
                      placeholder="John Doe"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      required
                      value={formData.customer_email}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, customer_email: e.target.value }))
                      }
                      placeholder="john@example.com"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={formData.customer_phone}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, customer_phone: e.target.value }))
                    }
                    placeholder="+44 7700 900000"
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="font-semibold">Service</h3>
                <div className="space-y-2">
                  <Label htmlFor="service">Service Type *</Label>
                  <select
                    id="service"
                    required
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={formData.service_name}
                    onChange={(e) => handleServiceChange(e.target.value)}
                  >
                    <option value="">Select a service...</option>
                    {SERVICES.map((s) => (
                      <option key={s.name} value={s.name}>
                        {s.name} {s.price > 0 ? `- ${formatPence(s.price)}` : "- Quote required"}
                      </option>
                    ))}
                  </select>
                </div>

                {isCustom && (
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="total">Total Amount (£) *</Label>
                      <Input
                        id="total"
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        onChange={(e) => {
                          const total = Math.round(parseFloat(e.target.value || "0") * 100);
                          setFormData((prev) => ({
                            ...prev,
                            total_amount_pence: total,
                            deposit_amount_pence: Math.round(total * 0.5),
                          }));
                        }}
                        placeholder="0.00"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="deposit">Deposit Amount (£) *</Label>
                      <Input
                        id="deposit"
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={(formData.deposit_amount_pence / 100).toFixed(2)}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            deposit_amount_pence: Math.round(parseFloat(e.target.value || "0") * 100),
                          }))
                        }
                        placeholder="0.00"
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="date">Preferred Date *</Label>
                  <Input
                    id="date"
                    type="date"
                    required
                    value={formData.booking_date.split("T")[0]}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, booking_date: e.target.value + "T10:00:00Z" }))
                    }
                    min={new Date().toISOString().split("T")[0]}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes">Additional Notes</Label>
                  <textarea
                    id="notes"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[80px]"
                    value={formData.notes}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, notes: e.target.value }))
                    }
                    placeholder="Any special requirements..."
                  />
                </div>
              </div>

              {formData.total_amount_pence > 0 && (
                <>
                  <Separator />
                  <div className="bg-slate-50 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Total</span>
                      <span>{formatPence(formData.total_amount_pence)}</span>
                    </div>
                    <div className="flex justify-between font-semibold">
                      <span>Deposit Due Now (50%)</span>
                      <span>{formatPence(formData.deposit_amount_pence)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Remaining balance due on completion
                    </p>
                  </div>
                </>
              )}

              {error && (
                <div className="bg-destructive/10 text-destructive rounded-lg p-3 text-sm">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full py-6 text-lg"
                disabled={loading || !formData.service_name || !formData.total_amount_pence}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Creating booking...
                  </>
                ) : formData.deposit_amount_pence > 0 ? (
                  `Pay ${formatPence(formData.deposit_amount_pence)} Deposit`
                ) : (
                  "Confirm Booking"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
