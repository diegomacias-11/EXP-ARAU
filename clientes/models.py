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

class PreguntaCliente(models.Model):
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="preguntas"
    )
    texto = models.CharField(max_length=255)
    TIPO_CHOICES = (
        ("texto", "Texto libre"),
        ("opciones", "Opciones (desplegable)"),
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="texto")
    opciones = models.TextField(blank=True, default="")  # una por línea si tipo = opciones
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["orden"]

    def __str__(self):
        return f"{self.cliente.cliente} - {self.texto[:40]}"

    @property
    def opciones_list(self):
        if not self.opciones:
            return []
        return [s.strip() for s in self.opciones.splitlines() if s.strip()]

class EncuestaEvento(models.Model):
    evento = models.OneToOneField(
        "eventos.Evento",        # 👈 referencia al modelo en otra app
        on_delete=models.CASCADE,
        related_name="encuesta"
    )
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Encuesta de {self.evento.nombre}"

class RespuestaEncuesta(models.Model):
    encuesta = models.ForeignKey(
        EncuestaEvento,
        on_delete=models.CASCADE,
        related_name="respuestas"
    )
    pregunta = models.ForeignKey(
        PreguntaCliente,
        on_delete=models.SET_NULL,
        null=True
    )
    # Snapshot del texto de la pregunta al momento de responder
    pregunta_texto = models.CharField(max_length=255, blank=True, default="")
    respuesta = models.TextField(blank=True, null=True)

    def __str__(self):
        try:
            ptxt = self.pregunta.texto if self.pregunta else (self.pregunta_texto or "")
        except Exception:
            ptxt = self.pregunta_texto or ""
        rtxt = (self.respuesta or "")
        return f"{ptxt[:30]} - {rtxt[:30]}"


