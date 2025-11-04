from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import ClienteForm
from .models import Cliente, PreguntaCliente, RespuestaEncuesta
from django.db.models import Count
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

def configurar_encuesta(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    msg = ""

    def _clean_opciones(raw: str) -> str:
        try:
            lines = [s.strip() for s in (raw or "").splitlines()]
            # quitar vacíos y duplicados preservando orden
            seen = set()
            cleaned = []
            for s in lines:
                if not s:
                    continue
                if s in seen:
                    continue
                seen.add(s)
                cleaned.append(s)
            return "\n".join(cleaned)
        except Exception:
            return ""

    if request.method == "POST":
        # editar existente
        edit_id = request.POST.get("edit_id")
        if edit_id:
            p = get_object_or_404(PreguntaCliente, id=edit_id, cliente=cliente)
            # Permitir siempre cambios de texto
            p.texto = (request.POST.get("texto", p.texto) or "").strip()

            # Si la pregunta YA tiene respuestas, bloquear cambios de tipo/opciones
            tiene_respuestas = RespuestaEncuesta.objects.filter(pregunta=p).exists()
            if tiene_respuestas:
                # Mantener tipo/opciones originales y avisar al usuario
                msg = "Esta pregunta ya tiene respuestas. Para cambiar las opciones, elimínala y crea una nueva."
            else:
                p.tipo = (request.POST.get("tipo", p.tipo) or "texto").strip() or "texto"
                if p.tipo == "opciones":
                    opciones_raw = request.POST.get("opciones", "")
                    opciones_clean = _clean_opciones(opciones_raw)
                    if not opciones_clean:
                        msg = "Debe capturar al menos una opción (una por línea)."
                    p.opciones = opciones_clean
                else:
                    p.opciones = ""

            p.save(update_fields=["texto", "tipo", "opciones"])
            return redirect('configurar_encuesta', cliente_id=cliente.id)

        # crear nueva
        nueva_pregunta = (request.POST.get("texto") or "").strip()
        if nueva_pregunta:
            orden = cliente.preguntas.count() + 1
            tipo = (request.POST.get("tipo") or "texto").strip() or "texto"
            opciones = ""
            if tipo == "opciones":
                opciones = _clean_opciones(request.POST.get("opciones", ""))
                if not opciones:
                    msg = "Debe capturar al menos una opción (una por línea)."
            PreguntaCliente.objects.create(
                cliente=cliente, texto=nueva_pregunta, tipo=tipo, opciones=opciones, orden=orden
            )
            return redirect('configurar_encuesta', cliente_id=cliente.id)

    preguntas = list(cliente.preguntas.all().order_by("orden"))
    # Marcar cuáles preguntas ya tienen respuestas para deshabilitar edición de opciones
    res_counts = (
        RespuestaEncuesta.objects
        .filter(pregunta__cliente=cliente)
        .values('pregunta_id')
        .annotate(c=Count('id'))
    )
    has_resp = {rc['pregunta_id']: rc['c'] > 0 for rc in res_counts}
    for pr in preguntas:
        pr.has_respuestas = has_resp.get(pr.id, False)
    back_url = request.GET.get('next') or reverse('clientes_lista')

    return render(request, "clientes/encuesta.html", {
        "cliente": cliente,
        "preguntas": preguntas,
        "back_url": back_url,
        "msg": msg,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })

def eliminar_pregunta(request, cliente_id, pregunta_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    pregunta = get_object_or_404(PreguntaCliente, id=pregunta_id, cliente=cliente)
    next_url = request.POST.get('next') or reverse('configurar_encuesta', kwargs={'cliente_id': cliente.id})
    if request.method == "POST":
        # Elimina y reenumera los órdenes restantes 1..n para evitar huecos
        pregunta.delete()
        restantes = cliente.preguntas.all().order_by('orden')
        nuevo_orden = 1
        for p in restantes:
            if p.orden != nuevo_orden:
                p.orden = nuevo_orden
                p.save(update_fields=["orden"])
            nuevo_orden += 1
        return redirect(next_url)
    return redirect('configurar_encuesta', cliente_id=cliente.id)
