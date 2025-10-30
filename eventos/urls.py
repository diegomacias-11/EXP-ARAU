from django.urls import path
from . import views

urlpatterns = [
    path('lista/', views.lista_eventos, name='eventos_lista'),
    path('nuevo/', views.agregar_evento, name='agregar_evento'),
    path('editar/<int:pk>/', views.editar_evento, name='editar_evento'),
    path('eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
]
