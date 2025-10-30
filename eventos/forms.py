from django import forms
from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nombre', 'telefono', 'ticket']
        labels = {
            'nombre': 'Nombre del cliente',
            'telefono': 'Teléfono',
            'ticket': 'Monto del ticket',
        }
        widgets = {
            'telefono': forms.TextInput(attrs={
                'maxlength': '10',
                'inputmode': 'numeric',
                'pattern': r'\d{10}',
                'placeholder': '10 dígitos',
                'oninput': "this.value=this.value.replace(/\\D/g,'').slice(0,10);",
            })
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '') or ''
        digits = ''.join(ch for ch in telefono if ch.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError('El teléfono debe contener exactamente 10 dígitos.')
        return digits

