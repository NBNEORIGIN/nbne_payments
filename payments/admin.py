from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, PaymentSession, Transaction, Refund


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'phone', 'provider', 'provider_customer_id', 'created_at']
    list_filter = ['provider', 'created_at']
    search_fields = ['email', 'name', 'phone', 'provider_customer_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PaymentSession)
class PaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'payable_type', 'payable_id', 'amount_display', 'status', 'customer', 'created_at']
    list_filter = ['status', 'payable_type', 'provider', 'currency', 'created_at']
    search_fields = ['payable_id', 'stripe_checkout_session_id', 'stripe_payment_intent_id', 'idempotency_key']
    readonly_fields = ['created_at', 'updated_at', 'stripe_checkout_session_id', 'stripe_payment_intent_id', 'processed_events']
    raw_id_fields = ['customer']
    
    fieldsets = (
        ('Payable Information', {
            'fields': ('payable_type', 'payable_id', 'idempotency_key')
        }),
        ('Payment Details', {
            'fields': ('amount_pence', 'currency', 'status', 'provider')
        }),
        ('Customer', {
            'fields': ('customer',)
        }),
        ('Stripe Information', {
            'fields': ('stripe_checkout_session_id', 'stripe_payment_intent_id')
        }),
        ('URLs', {
            'fields': ('success_url', 'cancel_url')
        }),
        ('Metadata', {
            'fields': ('metadata', 'processed_events')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def amount_display(self, obj):
        return f"£{obj.amount_pence/100:.2f}"
    amount_display.short_description = 'Amount'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment_session', 'gross_amount_display', 'fee_amount_display', 'net_amount_display', 'captured_at']
    list_filter = ['currency', 'captured_at', 'created_at']
    search_fields = ['provider_charge_id', 'payment_session__stripe_checkout_session_id']
    readonly_fields = ['created_at', 'captured_at']
    raw_id_fields = ['payment_session']

    def gross_amount_display(self, obj):
        return f"£{obj.gross_amount_pence/100:.2f}"
    gross_amount_display.short_description = 'Gross'

    def fee_amount_display(self, obj):
        if obj.fee_amount_pence:
            return f"£{obj.fee_amount_pence/100:.2f}"
        return '-'
    fee_amount_display.short_description = 'Fee'

    def net_amount_display(self, obj):
        if obj.net_amount_pence:
            return f"£{obj.net_amount_pence/100:.2f}"
        return '-'
    net_amount_display.short_description = 'Net'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'transaction', 'amount_display', 'status', 'reason_short', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['provider_refund_id', 'reason']
    readonly_fields = ['created_at']
    raw_id_fields = ['transaction']

    def amount_display(self, obj):
        return f"£{obj.amount_pence/100:.2f}"
    amount_display.short_description = 'Amount'

    def reason_short(self, obj):
        if obj.reason:
            return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return '-'
    reason_short.short_description = 'Reason'
