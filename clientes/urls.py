from django.urls import path
from . import views

urlpatterns = [
    path('lista/', views.lista_clientes, name='clientes_lista'),
    path('nuevo/', views.agregar_cliente, name='agregar_cliente'),
    path('editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),
]
