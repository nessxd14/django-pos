from django.urls import path

from . import views

app_name = 'retail'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('pos/', views.pos, name='pos'),
    path('pos/ventas/', views.crear_venta_pos_view, name='crear_venta_pos'),
]
