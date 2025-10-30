from django.shortcuts import render, redirect, get_object_or_404
from .forms import ClienteForm
from .models import Cliente
from django.contrib.auth.models import User

def lista_clientes(request):
    clientes = Cliente.objects.select_related("agente").all()

    return render(request, "clientes/lista.html", {
        'clientes': clientes,
    })

def agregar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            if request.user.is_authenticated:
                cliente.agente = request.user
            cliente.save()
            return redirect("clientes_lista")
    else:
        form = ClienteForm()

    return render(request, "clientes/form.html", {
        "form": form
    })

def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect("clientes_lista")
    else:
        form = ClienteForm(instance=cliente)

    return render(request, "clientes/form.html", {
        "form": form
    })

def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente.delete()
        return redirect("clientes_lista")
    # Si no es POST, redirige al formulario de edición
    return redirect("editar_cliente", pk=pk)
