from django.db import models
from clientes.models import Cliente

class Evento(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="eventos"
    )
    nombre_cliente = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    costo_ticket = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.nombre} - {self.nombre_cliente} ({self.fecha_registro.date()})"


class RespuestaEncuesta(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="respuestas"
    )
    pregunta = models.CharField(max_length=255)
    respuesta = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["evento"]),
            models.Index(fields=["pregunta"]),
        ]

    def __str__(self):
        return f"{self.evento.cliente.nombre} | {self.pregunta}: {self.respuesta}"
