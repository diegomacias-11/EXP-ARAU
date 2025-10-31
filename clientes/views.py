from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import ClienteForm
from .models import Cliente
from django.contrib.auth.models import User

def lista_clientes(request):
    clientes = Cliente.objects.select_related("agente").all()
    # Filtro por agente (GET)
    agente_id = request.GET.get('agente')
    if agente_id:
        try:
            clientes = clientes.filter(agente_id=int(agente_id))
        except ValueError:
            pass
    # Opciones de agentes existentes en clientes
    agentes = (Cliente.objects
               .select_related('agente')
               .values('agente_id', 'agente__first_name', 'agente__last_name', 'agente__username')
               .distinct())

    return render(request, "clientes/lista.html", {
        'clientes': clientes,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
        'agentes': agentes,
        'agente_selected': agente_id or '',
    })

def agregar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            if request.user.is_authenticated:
                cliente.agente = request.user
            cliente.save()
            next_url = request.POST.get('next') or reverse('clientes_lista')
            return redirect(next_url)
    else:
        form = ClienteForm()
    back_url = request.GET.get('next') or reverse('clientes_lista')
    return render(request, "clientes/form.html", {
        "form": form,
        "back_url": back_url,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            next_url = request.POST.get('next') or reverse('clientes_lista')
            return redirect(next_url)
    else:
        form = ClienteForm(instance=cliente)
    back_url = request.GET.get('next') or reverse('clientes_lista')
    return render(request, "clientes/form.html", {
        "form": form,
        "back_url": back_url,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        next_url = request.POST.get('next') or reverse('clientes_lista')
        cliente.delete()
        return redirect(next_url)
    # Si no es POST, redirige al formulario de edición
    return redirect("editar_cliente", pk=pk)
