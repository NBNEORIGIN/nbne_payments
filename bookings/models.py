from django.db import models


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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT', db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings_booking'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.service_name} - {self.status}"

    def requires_payment(self):
        return self.deposit_amount_pence > 0
