"use client";

import Link from "next/link";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BookingCancelPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <h1 className="text-xl font-bold tracking-tight">NBNE Signs</h1>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 py-16">
        <Card>
          <CardHeader className="text-center space-y-4">
            <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto">
              <XCircle className="w-10 h-10 text-orange-500" />
            </div>
            <CardTitle className="text-2xl">Payment Cancelled</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-center">
            <p className="text-muted-foreground">
              Your payment was cancelled. No charge has been made.
              Your booking has not been confirmed.
            </p>
            <div className="flex gap-3">
              <Link href="/booking/new" className="flex-1">
                <Button variant="outline" className="w-full">Try Again</Button>
              </Link>
              <Link href="/" className="flex-1">
                <Button className="w-full">Return Home</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
