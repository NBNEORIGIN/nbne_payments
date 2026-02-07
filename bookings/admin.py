from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'service_name', 'booking_date', 'status', 'deposit_display', 'created_at']
    list_filter = ['status', 'booking_date', 'created_at']
    search_fields = ['customer_name', 'customer_email', 'service_name']
    readonly_fields = ['created_at', 'updated_at']

    def deposit_display(self, obj):
        return f"£{obj.deposit_amount_pence/100:.2f}"
    deposit_display.short_description = 'Deposit'
