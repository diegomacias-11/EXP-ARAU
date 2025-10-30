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
        # Enforce 10-digit phone at the widget level (no reload needed)
        if 'num_contacto' in self.fields:
            self.fields['num_contacto'].widget.attrs.update({
                'maxlength': '10',
                'inputmode': 'numeric',
                'pattern': r'\d{10}',
                'placeholder': '10 dígitos',
                'oninput': "this.value=this.value.replace(/\\D/g,'').slice(0,10);",
            })

    def clean_num_contacto(self):
        num = self.cleaned_data.get('num_contacto', '') or ''
        digits = ''.join(ch for ch in num if ch.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError('El teléfono debe contener exactamente 10 dígitos.')
        return digits
