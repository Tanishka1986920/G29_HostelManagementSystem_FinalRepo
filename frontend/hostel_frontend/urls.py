from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),  # New route
    path('dashboard/', views.dashboard, name='dashboard'),
    path('rooms/', views.rooms, name='rooms'),
    path('students/', views.students, name='students'),
    path('bookings/', views.bookings, name='bookings'),
    path('notices/', views.notices, name='notices'),
    path('leave-requests/', views.leave_requests, name='leave_requests'),
    path('logout/', views.logout_view, name='logout'),
]
