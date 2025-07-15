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

def index(request):
    """Vista principal del sistema del puente"""
    return render(request, 'index.html')

@csrf_exempt
@require_http_methods(["POST"])
def registrar_auto(request):
    """Registrar un nuevo auto en el sistema"""
    try:
        data = json.loads(request.body)
        auto = Auto.objects.create(
            nombre=data.get('nombre', f'Auto_{random.randint(1000, 9999)}'),
            velocidad=data.get('velocidad', random.uniform(30, 80)),
            tiempo_espera=data.get('tiempo_espera', random.uniform(5, 15)),
            direccion=data.get('direccion', random.choice(['N', 'S']))
        )
        
        # Notificar a todos los clientes sobre el nuevo auto
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "puente_grupo",
            {
                "type": "auto_registrado",
                "auto": {
                    "id": auto.id,
                    "nombre": auto.nombre,
                    "direccion": auto.direccion,
                    "velocidad": auto.velocidad,
                    "tiempo_espera": auto.tiempo_espera
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'auto_id': auto.id,
            'message': f'Auto {auto.nombre} registrado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def solicitar_cruce(request):
    """Solicitar permiso para cruzar el puente"""
    try:
        data = json.loads(request.body)
        auto_id = data.get('auto_id')
        
        try:
            auto = Auto.objects.get(id=auto_id)
        except Auto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Auto no encontrado'
            }, status=404)
        
        # Lógica de control del puente
        autos_en_puente = Auto.objects.filter(en_puente=True)
        
        if autos_en_puente.exists():
            # Si hay autos en el puente, verificar dirección
            auto_en_puente = autos_en_puente.first()
            if auto_en_puente.direccion != auto.direccion:
                # Dirección diferente, debe esperar
                return JsonResponse({
                    'success': False,
                    'permiso': False,
                    'mensaje': f'Puente ocupado por auto en dirección {auto_en_puente.get_direccion_display()}'
                })
        
        # Dar permiso para cruzar
        auto.en_puente = True
        auto.save()
        
        # Notificar a todos los clientes
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "puente_grupo",
            {
                "type": "auto_cruzando",
                "auto": {
                    "id": auto.id,
                    "nombre": auto.nombre,
                    "direccion": auto.direccion
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'permiso': True,
            'mensaje': f'Auto {auto.nombre} puede cruzar el puente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def finalizar_cruce(request):
    """Finalizar el cruce del puente"""
    try:
        data = json.loads(request.body)
        auto_id = data.get('auto_id')
        
        try:
            auto = Auto.objects.get(id=auto_id)
        except Auto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Auto no encontrado'
            }, status=404)
        
        auto.en_puente = False
        auto.save()
        
        # Notificar a todos los clientes
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "puente_grupo",
            {
                "type": "auto_salio",
                "auto": {
                    "id": auto.id,
                    "nombre": auto.nombre,
                    "direccion": auto.direccion
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'mensaje': f'Auto {auto.nombre} ha salido del puente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def estado_puente(request):
    """Obtener el estado actual del puente"""
    autos_en_puente = Auto.objects.filter(en_puente=True)
    autos_esperando = Auto.objects.filter(en_puente=False)
    
    return JsonResponse({
        'autos_en_puente': list(autos_en_puente.values()),
        'autos_esperando': list(autos_esperando.values()),
        'total_autos': Auto.objects.count()
    })
