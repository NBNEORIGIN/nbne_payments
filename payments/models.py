from django.db import models
from django.utils import timezone


class Customer(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    provider = models.CharField(max_length=50, default='stripe')
    provider_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments_customer'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.provider})"


class PaymentSession(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]

    payable_type = models.CharField(max_length=100, db_index=True)
    payable_id = models.CharField(max_length=255, db_index=True)
    amount_pence = models.IntegerField()
    currency = models.CharField(max_length=3, default='GBP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', db_index=True)
    provider = models.CharField(max_length=50, default='stripe')
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_sessions')
    success_url = models.TextField()
    cancel_url = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    processed_events = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments_session'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payable_type', 'payable_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.payable_type}:{self.payable_id} - {self.status} - {self.amount_pence/100:.2f} {self.currency}"

    def mark_event_processed(self, event_id):
        if event_id not in self.processed_events:
            self.processed_events.append(event_id)
            self.save(update_fields=['processed_events', 'updated_at'])
            return True
        return False


class Transaction(models.Model):
    payment_session = models.ForeignKey(PaymentSession, on_delete=models.CASCADE, related_name='transactions')
    gross_amount_pence = models.IntegerField()
    fee_amount_pence = models.IntegerField(null=True, blank=True)
    net_amount_pence = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='GBP')
    captured_at = models.DateTimeField(default=timezone.now)
    provider_charge_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments_transaction'
        ordering = ['-captured_at']

    def __str__(self):
        return f"Transaction {self.id} - {self.gross_amount_pence/100:.2f} {self.currency}"


class Refund(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='refunds')
    amount_pence = models.IntegerField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    provider_refund_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments_refund'
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.id} - {self.amount_pence/100:.2f} - {self.status}"
