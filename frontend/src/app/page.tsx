import Link from "next/link";
import { PenLine, CreditCard, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">NBNE Signs</h1>
          <Link href="/booking/lookup">
            <Button variant="outline" size="sm">Check Booking Status</Button>
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold tracking-tight mb-4">
            Book Your Sign Service
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Professional signage solutions for your business. Book online and pay securely with Stripe.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <Card className="text-center p-6">
            <CardContent className="pt-6 space-y-4">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                <PenLine className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold text-lg">1. Fill in Details</h3>
              <p className="text-sm text-muted-foreground">
                Tell us about your project and choose your service
              </p>
            </CardContent>
          </Card>

          <Card className="text-center p-6">
            <CardContent className="pt-6 space-y-4">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                <CreditCard className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold text-lg">2. Pay Deposit</h3>
              <p className="text-sm text-muted-foreground">
                Secure your booking with a deposit via Stripe Checkout
              </p>
            </CardContent>
          </Card>

          <Card className="text-center p-6">
            <CardContent className="pt-6 space-y-4">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold text-lg">3. Confirmed</h3>
              <p className="text-sm text-muted-foreground">
                Your booking is confirmed and we&apos;ll be in touch
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="text-center">
          <Link href="/booking/new">
            <Button size="lg" className="text-lg px-8 py-6">
              Book Now
            </Button>
          </Link>
        </div>
      </main>

      <footer className="border-t mt-24">
        <div className="max-w-5xl mx-auto px-4 py-8 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} NBNE Signs. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
