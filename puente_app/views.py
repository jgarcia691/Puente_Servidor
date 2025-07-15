from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import random
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Auto

LONGITUD_PUENTE = 500  # metros

def index(request):
    """Vista principal del sistema del puente"""
    return render(request, 'index.html')

@csrf_exempt
@require_http_methods(["POST"])
def registrar_auto(request):
    """Registrar un nuevo auto en el sistema, asignando dirección, velocidad, turno y tiempos automáticamente"""
    try:
        # Dirección aleatoria
        direccion = random.choice(['N', 'S'])
        # Velocidad aleatoria entre 20 y 60 km/h
        velocidad = random.uniform(20, 60)
        # Obtener la cola correspondiente
        cola = Auto.objects.filter(direccion=direccion).order_by('turno')
        turno = cola.count() + 1
        # Calcular tiempo de cruce (en segundos)
        velocidad_m_s = velocidad * 1000 / 3600  # convertir km/h a m/s
        tiempo_cruce = LONGITUD_PUENTE / velocidad_m_s
        # Calcular tiempo de espera: suma de los tiempos de cruce de los autos delante
        tiempo_espera = sum([a.tiempo_cruce for a in cola])
        # Crear el auto
        auto = Auto.objects.create(
            direccion=direccion,
            velocidad=velocidad,
            turno=turno,
            tiempo_cruce=tiempo_cruce,
            tiempo_espera=tiempo_espera
        )
        return JsonResponse({
            'success': True,
            'auto_id': auto.id,
            'direccion': auto.get_direccion_display(),
            'velocidad': round(auto.velocidad, 2),
            'turno': auto.turno,
            'tiempo_cruce': round(auto.tiempo_cruce, 2),
            'tiempo_espera': round(auto.tiempo_espera, 2),
            'message': f'Auto registrado exitosamente en la cola {auto.get_direccion_display()}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def solicitar_cruce(request):
    """Permitir el cruce solo al auto con turno 1 en su cola"""
    try:
        data = json.loads(request.body)
        auto_id = data.get('auto_id')
        auto = Auto.objects.get(id=auto_id)
        # Buscar el auto con turno 1 en la cola correspondiente
        primero = Auto.objects.filter(direccion=auto.direccion).order_by('turno').first()
        if primero and primero.id == auto.id:
            return JsonResponse({
                'success': True,
                'permiso': True,
                'mensaje': f'Auto {auto.id} puede cruzar el puente',
                'tiempo_cruce': round(auto.tiempo_cruce, 2)
            })
        else:
            return JsonResponse({
                'success': False,
                'permiso': False,
                'mensaje': 'No es tu turno para cruzar el puente.'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def finalizar_cruce(request):
    """Eliminar el auto que cruzó y actualizar turnos y tiempos de espera de la cola"""
    try:
        data = json.loads(request.body)
        auto_id = data.get('auto_id')
        auto = Auto.objects.get(id=auto_id)
        direccion = auto.direccion
        # Eliminar el auto que cruzó
        auto.delete()
        # Actualizar turnos y tiempos de espera de los autos restantes en la cola
        cola = Auto.objects.filter(direccion=direccion).order_by('turno')
        tiempo_acumulado = 0
        for idx, a in enumerate(cola, start=1):
            velocidad_m_s = a.velocidad * 1000 / 3600
            tiempo_cruce = LONGITUD_PUENTE / velocidad_m_s
            a.turno = idx
            a.tiempo_espera = tiempo_acumulado
            a.tiempo_cruce = tiempo_cruce
            a.save()
            tiempo_acumulado += tiempo_cruce
        return JsonResponse({
            'success': True,
            'mensaje': 'Cruce finalizado y cola actualizada.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def estado_puente(request):
    """Mostrar el auto que está cruzando (turno 1 de cada cola) y las colas restantes"""
    auto_norte = Auto.objects.filter(direccion='N').order_by('turno').first()
    auto_sur = Auto.objects.filter(direccion='S').order_by('turno').first()
    cola_norte = list(Auto.objects.filter(direccion='N', turno__gt=1).order_by('turno').values('id', 'turno', 'velocidad', 'tiempo_cruce', 'tiempo_espera'))
    cola_sur = list(Auto.objects.filter(direccion='S', turno__gt=1).order_by('turno').values('id', 'turno', 'velocidad', 'tiempo_cruce', 'tiempo_espera'))
    return JsonResponse({
        'cruzando_norte': {
            'id': auto_norte.id,
            'turno': auto_norte.turno,
            'velocidad': round(auto_norte.velocidad, 2),
            'tiempo_cruce': round(auto_norte.tiempo_cruce, 2),
            'tiempo_espera': round(auto_norte.tiempo_espera, 2)
        } if auto_norte else None,
        'cruzando_sur': {
            'id': auto_sur.id,
            'turno': auto_sur.turno,
            'velocidad': round(auto_sur.velocidad, 2),
            'tiempo_cruce': round(auto_sur.tiempo_cruce, 2),
            'tiempo_espera': round(auto_sur.tiempo_espera, 2)
        } if auto_sur else None,
        'cola_norte': cola_norte,
        'cola_sur': cola_sur
    })

def estado_colas(request):
    """Obtener el estado actual de las colas Norte y Sur"""
    cola_norte = Auto.objects.filter(direccion='N').order_by('turno')
    cola_sur = Auto.objects.filter(direccion='S').order_by('turno')
    return JsonResponse({
        'cola_norte': [
            {
                'id': a.id,
                'turno': a.turno,
                'velocidad': round(a.velocidad, 2),
                'tiempo_cruce': round(a.tiempo_cruce, 2),
                'tiempo_espera': round(a.tiempo_espera, 2)
            } for a in cola_norte
        ],
        'cola_sur': [
            {
                'id': a.id,
                'turno': a.turno,
                'velocidad': round(a.velocidad, 2),
                'tiempo_cruce': round(a.tiempo_cruce, 2),
                'tiempo_espera': round(a.tiempo_espera, 2)
            } for a in cola_sur
        ]
    })
