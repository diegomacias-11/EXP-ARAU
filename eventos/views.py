from django.shortcuts import render, redirect, get_object_or_404
from .models import Evento
from django.urls import reverse
from .forms import EventoForm

def lista_eventos(request):
    if request.user.groups.filter(name='Cliente').exists():
        eventos = Evento.objects.filter(cliente=request.user)
    else:
        eventos = Evento.objects.select_related("cliente").all()

    return render(request, "eventos/lista.html", {
        "eventos": eventos,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def agregar_evento(request):
    if request.method == "POST":
        form = EventoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            if request.user.is_authenticated:
                evento.cliente = request.user
            evento.save()
            return redirect("eventos_lista")
    else:
        form = EventoForm()

    back_url = request.GET.get('next') or reverse('eventos_lista')
    return render(request, "eventos/form.html", {
        "form": form,
        "puede_eliminar": False,
        "back_url": back_url,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def editar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)

    if request.method == "POST":
        form = EventoForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            next_url = request.POST.get('next') or reverse('eventos_lista')
            return redirect(next_url)
    else:
        form = EventoForm(instance=evento)

    back_url = request.GET.get('next') or reverse('eventos_lista')
    return render(request, "eventos/form.html", {
        "form": form,
        "puede_eliminar": not request.user.groups.filter(name='Cliente').exists(),
        "back_url": back_url,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def eliminar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)

    if request.user.groups.filter(name="Cliente").exists():
        return redirect("eventos_lista")

    if request.method == "POST":
        next_url = request.POST.get('next') or reverse('eventos_lista')
        evento.delete()
        return redirect(next_url)

    return redirect("editar_evento", pk=pk)
