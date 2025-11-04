from django.urls import path
from . import views

urlpatterns = [
    path('lista/', views.lista_eventos, name='eventos_lista'),
    path('nuevo/', views.agregar_evento, name='agregar_evento'),
    path('editar/<int:pk>/', views.editar_evento, name='editar_evento'),
    path('eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
    path('encuesta/<int:pk>/', views.encuesta_evento, name='eventos_encuesta'),
    # Reportes (solo agentes)
    path('reportes/', views.reportes_dashboard, name='reportes_dashboard'),
    path('reportes/data/', views.reportes_data, name='reportes_data'),
]
