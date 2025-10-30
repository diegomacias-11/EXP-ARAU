from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("cliente", "agente", "usuario_asociado", "fecha_registro")
    search_fields = ("cliente", "contacto", "correo")