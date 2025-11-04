from django.contrib import admin
from .models import Evento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "cliente", "telefono", "ticket", "fecha_registro", "encuesta_completada")
    list_select_related = ("cliente",)
    search_fields = (
        "nombre",
        "telefono",
        "cliente__username",
        "cliente__email",
        "cliente__first_name",
        "cliente__last_name",
    )
    list_filter = ("fecha_registro",)
    readonly_fields = ("fecha_registro", "preguntas_respuestas", "encuesta_completada")
    ordering = ("-fecha_registro",)
    date_hierarchy = "fecha_registro"
    fields = (
        "cliente",
        "nombre",
        "telefono",
        "ticket",
        "fecha_registro",
        "encuesta_completada",
        "preguntas_respuestas",
    )

    def encuesta_completada(self, obj):
        try:
            enc = getattr(obj, "encuesta", None)
            return bool(enc and enc.respuestas.exists())
        except Exception:
            return False
    encuesta_completada.boolean = True
    encuesta_completada.short_description = "Encuesta"

    def preguntas_respuestas(self, obj):
        try:
            enc = getattr(obj, "encuesta", None)
            if not enc:
                return ""
            pares = []
            for r in enc.respuestas.select_related("pregunta").all():
                p = getattr(r, "pregunta", None)
                ptxt = getattr(p, "texto", "") if p else ""
                atxt = r.respuesta or ""
                pares.append(f"- {ptxt}: {atxt}")
            return "\n".join(pares)
        except Exception:
            return ""
    preguntas_respuestas.short_description = "Preguntas y respuestas"
    preguntas_respuestas.allow_tags = False
