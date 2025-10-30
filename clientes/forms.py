from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['cliente', 'num_eventos', 'contacto', 'num_contacto', 'correo', 'usuario_asociado']
        labels = {
            'cliente': 'Nombre del cliente',
            'num_eventos': 'Número de eventos',
            'contacto': 'Contacto',
            'num_contacto': 'Teléfono',
            'correo': 'Correo',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario_asociado'].disabled = True