from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    cliente = models.CharField(max_length=200)
    agente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="clientes_asignados"
    )
    num_eventos = models.IntegerField(default=0)
    contacto = models.CharField(max_length=200)
    num_contacto = models.CharField(max_length=20)
    correo = models.EmailField(null=True, blank=True)
    usuario_asociado = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_cliente"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.contacto:
            self.contacto = self.contacto.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.cliente
