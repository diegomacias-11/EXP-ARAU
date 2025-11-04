from django.db import models
from django.contrib.auth.models import User


class Evento(models.Model):
    cliente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="eventos"
    )
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    ticket = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre}"
