from django.shortcuts import render

def crear_evento(request):
    return render(request, "eventos/crear.html")

def responder_encuesta(request, evento_id):
    return render(request, "eventos/responder.html", {"evento_id": evento_id})
