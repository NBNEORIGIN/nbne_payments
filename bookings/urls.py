from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_booking, name='create_booking'),
    path('<int:booking_id>/', views.get_booking, name='get_booking'),
    path('<int:booking_id>/confirm-payment/', views.confirm_booking_payment, name='confirm_booking_payment'),
    path('<int:booking_id>/payment-success/', views.payment_success, name='payment_success'),
    path('<int:booking_id>/payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('webhook/payment/', views.payment_webhook_callback, name='payment_webhook_callback'),
]
