from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('verify-captcha/', views.verify_captcha, name='verify_captcha'),
    path('generate-captcha/', views.generate_captcha, name='generate_captcha'),
    path('check-display-name/', views.CheckDisplayNameView.as_view(), name='check_display_name'),
]
