from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.create_checkout_session, name='create_checkout_session'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('status/<int:payment_session_id>/', views.get_payment_status, name='get_payment_status'),
]
