from django.urls import path
from . import views

urlpatterns = [
    path("crear/", views.crear_evento, name="eventos_crear"),
    path("<int:evento_id>/responder/", views.responder_encuesta, name="eventos_responder"),
]
