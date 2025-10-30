from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    cliente = models.CharField(max_length=200)
    agente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="clientes_asignados"
    )
    num_eventos = models.IntegerField()
    contacto = models.CharField(max_length=200)
    num_contacto =  models.IntegerField()
    correo = models.CharField(max_length=200, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
