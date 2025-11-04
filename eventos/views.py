from django.shortcuts import render, redirect, get_object_or_404
from .models import Evento
from clientes.models import Cliente
from clientes.models import Cliente
from django.urls import reverse
from .forms import EventoForm
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.db.models import Count, Avg, Sum
from django.db.models.functions import TruncDate

def lista_eventos(request):
    if request.user.groups.filter(name='Cliente').exists():
        # Un cliente sólo ve sus propios eventos
        eventos = Evento.objects.filter(cliente=request.user)
    elif request.user.groups.filter(name='Agente').exists():
        # Un agente ve eventos de los usuarios (clientes) asignados en Cliente.agente
        clientes_asignados = Cliente.objects.filter(agente=request.user).values('usuario_asociado')
        eventos = Evento.objects.filter(cliente__in=clientes_asignados)
    else:
        eventos = Evento.objects.select_related("cliente").all()

    # Filtros por fecha (GET)
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    if fecha_desde:
        try:
            eventos = eventos.filter(fecha_registro__date__gte=fecha_desde)
        except Exception:
            pass
    if fecha_hasta:
        try:
            eventos = eventos.filter(fecha_registro__date__lte=fecha_hasta)
        except Exception:
            pass

    return render(request, "eventos/lista.html", {
        "eventos": eventos,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
        'is_agente': request.user.groups.filter(name='Agente').exists(),
        'fecha_desde': fecha_desde or '',
        'fecha_hasta': fecha_hasta or '',
    })

def agregar_evento(request):
    # Bloquear acceso a creación para usuarios del grupo Agente
    if request.user.groups.filter(name='Agente').exists():
        return redirect("eventos_lista")
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

def encuesta_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    # Buscar el perfil Cliente enlazado al usuario del evento
    cliente_perfil = Cliente.objects.filter(usuario_asociado=evento.cliente).first()
    preguntas = cliente_perfil.preguntas.all() if cliente_perfil else []
    back_url = request.GET.get('next') or reverse('eventos_lista')

    # Cargar/crear encuesta asociada al evento
    from clientes.models import EncuestaEvento, RespuestaEncuesta
    encuesta = None
    try:
        encuesta = EncuestaEvento.objects.get(evento=evento)
    except EncuestaEvento.DoesNotExist:
        encuesta = None

    if request.method == "POST":
        # Asegurar objeto encuesta
        if encuesta is None:
            encuesta = EncuestaEvento.objects.create(evento=evento)
        # Guardar respuestas por pregunta
        for p in preguntas:
            key = f"respuesta_{p.id}"
            val = request.POST.get(key, "").strip()
            try:
                if getattr(p, 'tipo', 'texto') == 'opciones':
                    # si no está en opciones, considerar vacío
                    opts = list(getattr(p, 'opciones_list', []) or [])
                    if val and val not in opts:
                        val = ""
            except Exception:
                pass
            if not val and encuesta.respuestas.filter(pregunta=p).exists():
                # Si se envía vacío, eliminar respuesta existente
                encuesta.respuestas.filter(pregunta=p).delete()
                continue
            if val:
                obj, _ = RespuestaEncuesta.objects.get_or_create(encuesta=encuesta, pregunta=p)
                obj.pregunta = p
                try:
                    obj.pregunta_texto = p.texto
                except Exception:
                    pass
                obj.respuesta = val
                obj.save(update_fields=["pregunta", "pregunta_texto", "respuesta"])
        next_url = request.POST.get('next') or back_url
        return redirect(next_url)

    # Prefill respuestas existentes
    respuestas = {}
    if encuesta is not None:
        for r in encuesta.respuestas.select_related('pregunta').all():
            respuestas[r.pregunta_id] = r.respuesta or ""

    # Adjuntar respuesta a cada pregunta para renderizar en template
    for p in preguntas:
        try:
            p.respuesta = respuestas.get(p.id, "")
        except Exception:
            p.respuesta = ""

    return render(request, "eventos/encuesta.html", {
        "evento": evento,
        "cliente": cliente_perfil,
        "preguntas": preguntas,
        "back_url": back_url,
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
    })


def _is_agente(user):
    return user.is_authenticated and user.groups.filter(name='Agente').exists()


def reportes_dashboard(request):
    if not _is_agente(request.user):
        return HttpResponseForbidden("Acceso restringido a Agentes")

    clientes = Cliente.objects.filter(agente=request.user).select_related('usuario_asociado').order_by('cliente')
    return render(request, "reportes/dashboard.html", {
        'is_cliente': request.user.groups.filter(name='Cliente').exists(),
        'clientes': clientes,
    })


def reportes_data(request):
    if not _is_agente(request.user):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cliente_id = request.GET.get('cliente_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if not cliente_id:
        return JsonResponse({'error': 'cliente_id requerido'}, status=400)

    # Validar cliente pertenece al agente
    cliente = get_object_or_404(Cliente.objects.filter(agente=request.user), pk=cliente_id)
    user_cliente = cliente.usuario_asociado  # User asociado a este Cliente

    qs = Evento.objects.select_related('cliente').filter(cliente=user_cliente)
    if fecha_desde:
        try:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        except Exception:
            pass
    if fecha_hasta:
        try:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        except Exception:
            pass

    # Serie: eventos por día
    por_dia = (
        qs.annotate(d=TruncDate('fecha_registro'))
        .values('d')
        .annotate(c=Count('id'))
        .order_by('d')
    )
    labels_dia = [str(i['d']) for i in por_dia]
    data_dia = [i['c'] for i in por_dia]

    # Encuestas completadas vs pendientes
    completadas = 0
    pendientes = 0
    eventos_data = []
    # Cargar preguntas/respuestas por evento
    try:
        from clientes.models import EncuestaEvento, PreguntaCliente, RespuestaEncuesta
    except Exception:
        EncuestaEvento = None
        PreguntaCliente = None
        RespuestaEncuesta = None

    for ev in qs.order_by('-fecha_registro'):
        qa = []
        hay_respuestas = False
        if hasattr(ev, 'encuesta') and ev.encuesta is not None:
            for r in ev.encuesta.respuestas.select_related('pregunta').all():
                ptxt = (getattr(r.pregunta, 'texto', None) if r.pregunta else None) or (r.pregunta_texto or '')
                p_id = getattr(r.pregunta, 'id', None)
                atxt = r.respuesta or ''
                if atxt:
                    hay_respuestas = True
                qa.append({'pregunta_id': p_id, 'pregunta': ptxt, 'respuesta': atxt})

        if hay_respuestas:
            completadas += 1
        else:
            pendientes += 1

        eventos_data.append({
            'id': ev.id,
            'nombre': ev.nombre,
            'telefono': ev.telefono,
            'ticket': str(ev.ticket),
            'fecha_registro': ev.fecha_registro.isoformat(),
            'completada': hay_respuestas,
            'qa': qa,
        })

    # Series por pregunta (pie por pregunta)
    per_pregunta = []
    if PreguntaCliente is not None and RespuestaEncuesta is not None:
        preguntas = list(PreguntaCliente.objects.filter(cliente=cliente).order_by('orden'))
        ev_ids = list(qs.values_list('id', flat=True))
        if ev_ids:
            for p in preguntas:
                base_qs = RespuestaEncuesta.objects.filter(
                    encuesta__evento_id__in=ev_ids,
                    pregunta=p,
                )
                # Conteo por respuesta no vacía
                qs_resp = base_qs.exclude(respuesta__isnull=True).exclude(respuesta__exact="")
                agg = (
                    qs_resp.values('respuesta')
                    .annotate(c=Count('id'))
                    .order_by('-c')
                )
                labels = [r['respuesta'] for r in agg]
                data = [r['c'] for r in agg]

                # Ya no agregamos categoría "Sin respuesta"; se ignoran en gráficos

                per_pregunta.append({
                    'pregunta_id': p.id,
                    'pregunta': p.texto,
                    'labels': labels,
                    'data': data,
                })

            # Agregar gráficas para respuestas de preguntas eliminadas (huérfanas)
            huérfanas = RespuestaEncuesta.objects.filter(
                encuesta__evento_id__in=ev_ids,
                pregunta__isnull=True
            ).exclude(pregunta_texto__exact="")

            # agrupar por texto de pregunta
            textos = list(
                huérfanas.values('pregunta_texto').distinct()
            )
            for t in textos:
                texto = t.get('pregunta_texto') or "(Pregunta eliminada)"
                dist = (
                    huérfanas.filter(pregunta_texto=texto)
                    .exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=Count('id'))
                    .order_by('-c')
                )
                if dist:
                    labels = [d['respuesta'] for d in dist]
                    data = [d['c'] for d in dist]
                    per_pregunta.append({
                        'pregunta_id': None,
                        'pregunta': texto,
                        'labels': labels,
                        'data': data,
                    })

    # KPI: ticket promedio, total, recuento
    agg = qs.aggregate(avg=Avg('ticket'), total=Sum('ticket'), n=Count('id'))

    # Series y datos para PDF (mismas reglas que en reportes_data)
    from django.db.models import Count as _Count
    por_dia = (
        qs.annotate(d=TruncDate('fecha_registro'))
        .values('d')
        .annotate(c=_Count('id'))
        .order_by('d')
    )
    labels_dia = [str(i['d']) for i in por_dia]
    data_dia = [i['c'] for i in por_dia]

    completadas = 0
    pendientes = 0
    per_pregunta = []
    try:
        from clientes.models import PreguntaCliente, RespuestaEncuesta
    except Exception:
        PreguntaCliente = None
        RespuestaEncuesta = None

    if RespuestaEncuesta is not None:
        ev_ids_all = list(qs.values_list('id', flat=True))
        if ev_ids_all:
            con_resp = set(
                RespuestaEncuesta.objects.filter(encuesta__evento_id__in=ev_ids_all)
                .values_list('encuesta__evento_id', flat=True)
            )
            completadas = len(con_resp)
            pendientes = max(0, len(ev_ids_all) - completadas)

    if PreguntaCliente is not None and RespuestaEncuesta is not None:
        ev_ids = list(qs.values_list('id', flat=True))
        if ev_ids:
            preguntas = list(PreguntaCliente.objects.filter(cliente=cliente).order_by('orden'))
            for p in preguntas:
                base_qs = RespuestaEncuesta.objects.filter(
                    encuesta__evento_id__in=ev_ids,
                    pregunta=p,
                )
                dist = (
                    base_qs.exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': getattr(p, 'texto', str(p.pk)),
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })
            # Preguntas eliminadas usando snapshot
            hq = RespuestaEncuesta.objects.filter(
                encuesta__evento_id__in=ev_ids,
                pregunta__isnull=True
            ).exclude(pregunta_texto__exact="")
            textos = list(hq.values('pregunta_texto').distinct())
            for t in textos:
                texto = t.get('pregunta_texto') or "(Pregunta eliminada)"
                dist = (
                    hq.filter(pregunta_texto=texto)
                    .exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': texto,
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })

    # Series para graficas (como en reportes_data)
    from django.db.models import Count as _Count
    por_dia = (
        qs.annotate(d=TruncDate('fecha_registro'))
        .values('d')
        .annotate(c=_Count('id'))
        .order_by('d')
    )
    labels_dia = [str(i['d']) for i in por_dia]
    data_dia = [i['c'] for i in por_dia]

    completadas = 0
    pendientes = 0
    per_pregunta = []
    try:
        from clientes.models import PreguntaCliente, RespuestaEncuesta
    except Exception:
        PreguntaCliente = None
        RespuestaEncuesta = None

    if RespuestaEncuesta is not None:
        ev_ids_all = list(qs.values_list('id', flat=True))
        if ev_ids_all:
            con_resp = set(
                RespuestaEncuesta.objects.filter(encuesta__evento_id__in=ev_ids_all)
                .values_list('encuesta__evento_id', flat=True)
            )
            completadas = len(con_resp)
            pendientes = max(0, len(ev_ids_all) - completadas)

    if PreguntaCliente is not None and RespuestaEncuesta is not None:
        # Distribucion por respuesta, ignorando vacias
        preguntas = list(PreguntaCliente.objects.filter(cliente=cliente).order_by('orden'))
        ev_ids = list(qs.values_list('id', flat=True))
        if ev_ids:
            for p in preguntas:
                base_qs = RespuestaEncuesta.objects.filter(
                    encuesta__evento_id__in=ev_ids,
                    pregunta=p,
                )
                dist = (
                    base_qs.exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': getattr(p, 'texto', str(p.pk)),
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })
            # Preguntas eliminadas (usando snapshot pregunta_texto)
            hq = RespuestaEncuesta.objects.filter(
                encuesta__evento_id__in=ev_ids,
                pregunta__isnull=True
            ).exclude(pregunta_texto__exact="")
            textos = list(hq.values('pregunta_texto').distinct())
            for t in textos:
                texto = t.get('pregunta_texto') or "(Pregunta eliminada)"
                dist = (
                    hq.filter(pregunta_texto=texto)
                    .exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': texto,
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })

    return JsonResponse({
        'series': {
            'eventos_por_dia': {
                'labels': labels_dia,
                'data': data_dia,
            },
            'encuestas': {
                'labels': ['Completadas', 'Pendientes'],
                'data': [completadas, pendientes],
            }
        },
        'eventos': eventos_data,
        'per_pregunta': per_pregunta,
        'kpi': {
            'avg_ticket': str(agg['avg'] or 0),
            'total_ticket': str(agg['total'] or 0),
            'num_eventos': agg['n'] or 0,
        }
    })


def reportes_pdf(request):
    # Solo agentes
    if not _is_agente(request.user):
        return HttpResponseForbidden("Acceso restringido a Agentes")

    # Parámetros
    cliente_id = request.GET.get('cliente_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    if not cliente_id:
        return HttpResponse("cliente_id requerido", status=400)

    cliente = get_object_or_404(Cliente.objects.filter(agente=request.user), pk=cliente_id)
    user_cliente = cliente.usuario_asociado

    qs = Evento.objects.select_related('cliente').filter(cliente=user_cliente)
    if fecha_desde:
        try:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        except Exception:
            pass
    if fecha_hasta:
        try:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        except Exception:
            pass

    agg = qs.aggregate(avg=Avg('ticket'), total=Sum('ticket'), n=Count('id'))

    # Generar PDF con reportlab (inline)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
    except Exception:
        return HttpResponse("Falta dependencia reportlab. Instala con: pip install reportlab", status=500)

    import os
    from django.conf import settings

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte.pdf"'

    w, h = A4  # 595x842 pt aprox
    c = canvas.Canvas(response, pagesize=A4)

    # Cargar imagen de fondo
    bg_path = os.path.join(settings.BASE_DIR, 'documentos', 'MEMBRETE ARAU.png')
    bg = None
    if os.path.exists(bg_path):
        try:
            bg = ImageReader(bg_path)
        except Exception:
            bg = None

    def new_page():
        if bg:
            c.drawImage(bg, 0, 0, width=w, height=h, mask='auto')
        # Márgenes
        c.setFont('Helvetica-Bold', 14)
        c.setFillColorRGB(0.17, 0.19, 0.25)

    # Portada / primera página
    new_page()
    y = h - 30 * mm
    c.drawString(20 * mm, y, f"Reporte de Eventos - {cliente.cliente}")
    y -= 8 * mm
    rango = ''
    if fecha_desde:
        rango += f"desde {fecha_desde} "
    if fecha_hasta:
        rango += f"hasta {fecha_hasta}"
    c.setFont('Helvetica', 11)
    c.drawString(20 * mm, y, rango.strip())

    # KPIs
    y -= 12 * mm
    c.setFont('Helvetica-Bold', 12)
    c.drawString(20 * mm, y, f"Eventos: {agg['n'] or 0}")
    c.drawString(70 * mm, y, f"Ticket promedio: {float(agg['avg'] or 0):.2f}")
    c.drawRightString(w - 20 * mm, y, f"Total: {float(agg['total'] or 0):.2f}")

    # Construir series para graficas del PDF (igual que en dashboard)
    try:
        from django.db.models import Count as _Count
        # Eventos por dia
        _por_dia = (
            qs.annotate(d=TruncDate('fecha_registro'))
            .values('d')
            .annotate(c=_Count('id'))
            .order_by('d')
        )
        labels_dia = [str(i['d']) for i in _por_dia]
        data_dia = [i['c'] for i in _por_dia]
    except Exception:
        labels_dia, data_dia = [], []

    completadas = 0
    pendientes = 0
    per_pregunta = []
    try:
        from clientes.models import PreguntaCliente, RespuestaEncuesta
        ev_ids_all = list(qs.values_list('id', flat=True))
        if ev_ids_all:
            con_resp = set(
                RespuestaEncuesta.objects.filter(encuesta__evento_id__in=ev_ids_all)
                .values_list('encuesta__evento_id', flat=True)
            )
            completadas = len(con_resp)
            pendientes = max(0, len(ev_ids_all) - completadas)
        # Per-pregunta (ignora respuestas vacias)
        ev_ids = ev_ids_all
        if ev_ids:
            for p in PreguntaCliente.objects.filter(cliente=cliente).order_by('orden'):
                base_qs = RespuestaEncuesta.objects.filter(
                    encuesta__evento_id__in=ev_ids,
                    pregunta=p,
                )
                dist = (
                    base_qs.exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': getattr(p, 'texto', str(p.pk)),
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })
            # Huérfanas con snapshot
            hq = RespuestaEncuesta.objects.filter(
                encuesta__evento_id__in=ev_ids,
                pregunta__isnull=True
            ).exclude(pregunta_texto__exact="")
            textos = list(hq.values('pregunta_texto').distinct())
            for t in textos:
                texto = t.get('pregunta_texto') or "(Pregunta eliminada)"
                dist = (
                    hq.filter(pregunta_texto=texto)
                    .exclude(respuesta__isnull=True)
                    .exclude(respuesta__exact="")
                    .values('respuesta')
                    .annotate(c=_Count('id'))
                    .order_by('-c')
                )
                if dist:
                    per_pregunta.append({
                        'pregunta': texto,
                        'labels': [d['respuesta'] for d in dist],
                        'data': [d['c'] for d in dist],
                    })
    except Exception:
        pass

    # Graficas principales (eventos por dia y encuestas)
    y -= 20 * mm
    left = 20 * mm
    right = w - 20 * mm
    midx = (left + right) / 2
    chart_h = 55 * mm

    def draw_bar_chart(x, y0, width, height, labels, data, title=''):
        if not labels or not data:
            return 0
        c.setFont('Helvetica-Bold', 11)
        if title:
            c.drawString(x, y0 + height + 5, title)
        maxv = max(data) if data else 1
        maxv = max(1, float(maxv))
        nbars = len(data)
        gap = 4
        barw = (width - (nbars + 1) * gap) / max(1, nbars)
        c.setFillColorRGB(0.35, 0.73, 0.78)  # #59b9c7
        c.setStrokeColorRGB(0.17, 0.19, 0.25)  # #2b313f
        for i, v in enumerate(data):
            bh = 0 if maxv <= 0 else (float(v) / maxv) * (height - 16)
            bx = x + gap + i * (barw + gap)
            by = y0
            c.rect(bx, by, max(0, barw), max(0, bh), fill=1, stroke=1)
            c.setFont('Helvetica', 8)
            txt = f"{int(v)}"
            c.setFillColorRGB(0.1, 0.12, 0.15)
            c.drawCentredString(bx + barw / 2, by + bh + 2, txt)
        c.setFont('Helvetica', 7)
        for i, lab in enumerate(labels):
            bx = x + gap + i * (barw + gap)
            c.drawString(bx, y0 - 8, str(lab))
        return height + 16

    def _hex_to_rgb01(col):
        if isinstance(col, str) and col.startswith('#') and len(col) in (4, 7):
            hch = col[1:]
            if len(hch) == 3:
                hch = ''.join([ch * 2 for ch in hch])
            return (int(hch[0:2], 16) / 255.0, int(hch[2:4], 16) / 255.0, int(hch[4:6], 16) / 255.0)
        return (0.35, 0.73, 0.78)

    try:
        from reportlab.graphics.shapes import Drawing, Wedge
        from reportlab.graphics import renderPDF
        def draw_donut_chart(cx, cy, r, labels, data, colors, title=''):
            total = sum(float(v) for v in data) if data else 0
            if total <= 0:
                return
            if title:
                c.setFont('Helvetica-Bold', 11)
                c.drawCentredString(cx, cy + r + 10, title)
            d = Drawing(2 * r, 2 * r)
            start = 0
            for i, v in enumerate(data):
                extent = 360.0 * (float(v) / total) if total > 0 else 0
                fill = _hex_to_rgb01(colors[i % len(colors)])
                wdg = Wedge(r, r, r, start, start + extent, fillColor=None, strokeColor=None)
                wdg.fillColor = fill
                d.add(wdg)
                start += extent
            hole = Wedge(r, r, r * 0.6, 0, 360, fillColor=(1, 1, 1), strokeColor=None)
            d.add(hole)
            renderPDF.draw(d, c, cx - r, cy - r)
            c.setFont('Helvetica', 8)
            yy = cy - r - 10
            for i, (lab, v) in enumerate(zip(labels, data)):
                r1, g1, b1 = _hex_to_rgb01(colors[i % len(colors)])
                c.setFillColorRGB(r1, g1, b1)
                c.rect(cx - r, yy - 6, 6, 6, fill=1, stroke=0)
                c.setFillColorRGB(0.1, 0.12, 0.15)
                c.drawString(cx - r + 8, yy - 4, f"{lab}: {int(v)}")
                yy -= 10
    except Exception:
        def draw_donut_chart(*args, **kwargs):
            return

    # Render: barra y donut principales
    _ = draw_bar_chart(left, y, (midx - left - 5 * mm), chart_h, labels_dia, data_dia, 'Eventos por dia')
    try:
        donut_cx = midx + (right - midx) / 2
        donut_cy = y + chart_h / 2
        r0 = min((right - midx - 5 * mm) / 2.5, chart_h / 2.2)
        if r0 > 10:
            draw_donut_chart(donut_cx, donut_cy, r0, ['Completadas', 'Pendientes'], [completadas, pendientes], ['#2b313f', '#aebed2'], 'Encuestas')
    except Exception:
        pass

    y -= (chart_h + 15)

    # Graficas por pregunta (grid 2 por fila)
    if per_pregunta:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(20 * mm, y, 'Respuestas por pregunta')
        y -= 8 * mm
        col_w = (right - left - 5 * mm) / 2
        r1 = min(col_w / 2.5, 30 * mm)
        idx = 0
        for item in per_pregunta:
            if y < 40 * mm:
                c.showPage()
                new_page()
                y = h - 30 * mm
            col = idx % 2
            cx = left + (col * (col_w + 5 * mm)) + col_w / 2
            cy = y - (r1 + 12)
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(cx, y, (item.get('pregunta') or '')[:70])
            try:
                draw_donut_chart(cx, cy, r1, item.get('labels') or [], item.get('data') or [], ['#2b313f', '#59b9c7', '#aebed2', '#294369', '#4aa5b3', '#808b98'], '')
            except Exception:
                pass
            if col == 1:
                y -= (2 * r1 + 26)
            idx += 1
        if idx % 2 == 1:
            y -= (2 * r1 + 26)

    # Encabezados de tabla
    y -= 10 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawString(20 * mm, y, 'Evento')
    c.drawString(70 * mm, y, 'Teléfono')
    c.drawString(100 * mm, y, 'Ticket')
    c.drawString(125 * mm, y, 'Fecha')
    y -= 6 * mm
    c.setFont('Helvetica', 10)

    # Filas
    for ev in qs.order_by('-fecha_registro'):
        if y < 20 * mm:
            c.showPage()
            new_page()
            y = h - 30 * mm
            c.setFont('Helvetica-Bold', 10)
            c.drawString(20 * mm, y, 'Evento')
            c.drawString(70 * mm, y, 'Teléfono')
            c.drawString(100 * mm, y, 'Ticket')
            c.drawString(125 * mm, y, 'Fecha')
            y -= 6 * mm
            c.setFont('Helvetica', 10)
        c.drawString(20 * mm, y, (ev.nombre or '')[:35])
        c.drawString(70 * mm, y, ev.telefono or '')
        c.drawString(100 * mm, y, f"{float(ev.ticket or 0):.2f}")
        try:
            fecha_txt = ev.fecha_registro.strftime('%Y-%m-%d %H:%M')
        except Exception:
            fecha_txt = str(ev.fecha_registro)
        c.drawString(125 * mm, y, fecha_txt)
        y -= 6 * mm

    c.showPage()
    c.save()
    return response
