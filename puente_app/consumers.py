import json
from channels.generic.websocket import AsyncWebsocketConsumer
from heapq import heappush, heappop
import asyncio

class PuenteConsumer(AsyncWebsocketConsumer):
    # Variables de clase compartidas entre todas las conexiones
    autos = {}  # id: {info del auto}
    cola_espera = []  # priority queue: (prioridad, llegada, id_auto)
    autos_en_puente = None  # id del auto cruzando actualmente
    auto_id_counter = 1
    llegada_counter = 0
    _lock = asyncio.Lock()  # Para evitar condiciones de carrera

    async def connect(self):
        try:
            print(f"Connecting... channel_layer: {self.channel_layer}")
            if self.channel_layer:
                await self.channel_layer.group_add("puente_grupo", self.channel_name)
            await self.accept()
            estado = self.get_estado_puente()
            await self.send(text_data=json.dumps({
                'type': 'estado_inicial',
                'data': estado
            }))
            print("WebSocket connected successfully")
        except Exception as e:
            print(f"Error in connect: {e}")
            await self.accept()

    async def disconnect(self, close_code):
        try:
            if self.channel_layer:
                await self.channel_layer.group_discard("puente_grupo", self.channel_name)
        except Exception as e:
            print(f"Error in disconnect: {e}")

    async def receive(self, text_data):
        try:
            print(f"Received message: {text_data}")
            data = json.loads(text_data)
            message_type = data.get('type')
            
            async with self._lock:  # Proteger operaciones críticas
                if message_type == 'registrar_auto':
                    await self.handle_registrar_auto(data)
                elif message_type == 'solicitar_cruce':
                    await self.handle_solicitar_cruce(data)
                elif message_type == 'finalizar_cruce':
                    await self.handle_finalizar_cruce(data)
                elif message_type == 'resetear_sistema':
                    await self.handle_resetear_sistema()
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Tipo de mensaje no reconocido'
                    }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'JSON inválido'
            }))
        except Exception as e:
            print(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error interno: {str(e)}'
            }))

    def get_estado_puente(self):
        auto_en_puente = []
        if PuenteConsumer.autos_en_puente and PuenteConsumer.autos_en_puente in PuenteConsumer.autos:
            auto_en_puente = [PuenteConsumer.autos[PuenteConsumer.autos_en_puente]]
        
        cola_ordenada = sorted(PuenteConsumer.cola_espera)
        autos_esperando = [PuenteConsumer.autos[aid] for (_, _, aid) in cola_ordenada if aid in PuenteConsumer.autos]
        return {
            'autos_en_puente': auto_en_puente,
            'autos_esperando': autos_esperando,
            'total_autos': len(PuenteConsumer.autos)
        }

    async def handle_registrar_auto(self, data):
        try:
            auto_data = data.get('auto', {})
            auto_id = PuenteConsumer.auto_id_counter
            PuenteConsumer.auto_id_counter += 1
            prioridad = int(auto_data.get('prioridad', 3))
            llegada = PuenteConsumer.llegada_counter
            PuenteConsumer.llegada_counter += 1
            vueltas = int(auto_data.get('vueltas', 1))
            
            auto = {
                'id': auto_id,
                'nombre': auto_data.get('nombre', f'Auto_{auto_id}'),
                'velocidad': float(auto_data.get('velocidad', 60)),
                'tiempo_espera': float(auto_data.get('tiempo_espera', 10)),
                'direccion': auto_data.get('direccion', 'N'),
                'prioridad': prioridad,
                'en_puente': False,
                'llegada': llegada,
                'vueltas': vueltas,
                'vueltas_totales': vueltas,  # Guardar el total original
                'cruzadas': 0  # Contador de cruces completados
            }
            
            PuenteConsumer.autos[auto_id] = auto
            heappush(PuenteConsumer.cola_espera, (prioridad, llegada, auto_id))
            
            print(f"Auto registrado: {auto['nombre']} (ID: {auto_id})")
            
            if self.channel_layer:
                await self.channel_layer.group_send(
                    "puente_grupo",
                    {
                        "type": "auto_registrado",
                        "auto": auto
                    }
                )
                # Enviar estado actualizado a todos los clientes
                await self.channel_layer.group_send(
                    "puente_grupo",
                    {
                        "type": "estado_actualizado",
                        "estado": self.get_estado_puente()
                    }
                )
        except Exception as e:
            print(f"Error en handle_registrar_auto: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error al registrar auto: {str(e)}'
            }))

    async def handle_solicitar_cruce(self, data):
        try:
            auto_id = data.get('auto_id')
            print(f"Solicitud de cruce para auto ID: {auto_id}")
            
            # Verificar que el auto existe
            if auto_id not in PuenteConsumer.autos:
                await self.send(text_data=json.dumps({
                    'type': 'respuesta_cruce',
                    'data': {
                        'success': False,
                        'permiso': False,
                        'mensaje': 'Auto no encontrado en el sistema',
                        'auto_id': auto_id
                    }
                }))
                return
            
            # Solo el auto al frente de la cola puede cruzar y solo si el puente está libre
            if PuenteConsumer.cola_espera and PuenteConsumer.cola_espera[0][2] == auto_id:
                if PuenteConsumer.autos_en_puente is None:
                    PuenteConsumer.autos_en_puente = auto_id
                    heappop(PuenteConsumer.cola_espera)
                    PuenteConsumer.autos[auto_id]['en_puente'] = True
                    
                    resultado = {
                        'success': True,
                        'permiso': True,
                        'mensaje': f"Auto {PuenteConsumer.autos[auto_id]['nombre']} puede cruzar el puente",
                        'auto': PuenteConsumer.autos[auto_id],
                        'auto_id': auto_id
                    }
                    
                    print(f"Auto {PuenteConsumer.autos[auto_id]['nombre']} comenzando cruce")
                    
                    if self.channel_layer:
                        await self.channel_layer.group_send(
                            "puente_grupo",
                            {
                                "type": "auto_cruzando",
                                "auto": PuenteConsumer.autos[auto_id]
                            }
                        )
                else:
                    auto_en_puente = PuenteConsumer.autos.get(PuenteConsumer.autos_en_puente, {})
                    resultado = {
                        'success': False,
                        'permiso': False,
                        'mensaje': f"Puente ocupado por {auto_en_puente.get('nombre', 'auto desconocido')}",
                        'auto_id': auto_id
                    }
            else:
                # Encontrar quién está al frente de la cola
                proximo_auto = None
                if PuenteConsumer.cola_espera:
                    proximo_id = PuenteConsumer.cola_espera[0][2]
                    proximo_auto = PuenteConsumer.autos.get(proximo_id, {})
                
                mensaje = 'No es el turno de este auto para cruzar'
                if proximo_auto:
                    mensaje += f". Turno actual: {proximo_auto.get('nombre', 'Auto desconocido')}"
                
                resultado = {
                    'success': False,
                    'permiso': False,
                    'mensaje': mensaje,
                    'auto_id': auto_id
                }
            
            await self.send(text_data=json.dumps({
                'type': 'respuesta_cruce',
                'data': resultado
            }))
        except Exception as e:
            print(f"Error en handle_solicitar_cruce: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error al solicitar cruce: {str(e)}'
            }))

    async def handle_finalizar_cruce(self, data):
        auto_id = data.get('auto_id')
        if PuenteConsumer.autos_en_puente == auto_id:
            PuenteConsumer.autos_en_puente = None
            auto = PuenteConsumer.autos.get(auto_id)
            
            if auto:
                auto['en_puente'] = False
                auto['cruzadas'] += 1  # Incrementar contador de cruces
                
                # Determinar si el auto debe continuar o salir del sistema
                if auto['cruzadas'] < auto['vueltas_totales']:
                    # El auto debe hacer más cruces
                    # Cambiar dirección (ida y vuelta)
                    auto['direccion'] = 'S' if auto['direccion'] == 'N' else 'N'
                    auto['vueltas'] = auto['vueltas_totales'] - auto['cruzadas']  # Actualizar vueltas restantes
                    
                    # Generar nuevo orden de llegada para la cola (FIFO - se pone al final)
                    # Encontrar el valor máximo de llegada actual y agregar 1 para ir al final
                    max_llegada = 0
                    if PuenteConsumer.cola_espera:
                        max_llegada = max(item[1] for item in PuenteConsumer.cola_espera)
                    
                    llegada = max_llegada + 1
                    auto['llegada'] = llegada
                    
                    # Volver a agregar a la cola con la misma prioridad pero al final
                    heappush(PuenteConsumer.cola_espera, (auto['prioridad'], llegada, auto_id))
                    
                    print(f"Auto {auto['nombre']} regresó a la cola al final (FIFO) - Dirección: {auto['direccion']} - Llegada: {llegada}")
                    
                    # Mostrar el estado actual de la cola
                    cola_actual = sorted(PuenteConsumer.cola_espera)
                    print("Cola actual después del regreso:")
                    for i, (prioridad, llegada_cola, auto_id_cola) in enumerate(cola_actual):
                        auto_cola = PuenteConsumer.autos.get(auto_id_cola, {})
                        print(f"  {i+1}. {auto_cola.get('nombre', 'Desconocido')} (llegada: {llegada_cola})")
                    
                    # Notificar que el auto ha regresado a la cola
                    if self.channel_layer:
                        await self.channel_layer.group_send(
                            "puente_grupo",
                            {
                                "type": "auto_regreso_cola",
                                "auto": auto
                            }
                        )
                else:
                    # El auto ha completado todas sus vueltas, removerlo del sistema
                    PuenteConsumer.autos.pop(auto_id, None)
                    if self.channel_layer:
                        await self.channel_layer.group_send(
                            "puente_grupo",
                            {
                                "type": "auto_salio",
                                "auto": auto,
                                "eliminado": True
                            }
                        )
                
                # Notificar a todos los clientes el estado actualizado
                if self.channel_layer:
                    await self.channel_layer.group_send(
                        "puente_grupo",
                        {
                            "type": "estado_actualizado",
                            "estado": self.get_estado_puente()
                        }
                    )

    async def handle_resetear_sistema(self):
        # Limpiar completamente el sistema
        PuenteConsumer.autos.clear()
        PuenteConsumer.cola_espera.clear()
        PuenteConsumer.autos_en_puente = None
        PuenteConsumer.auto_id_counter = 1
        PuenteConsumer.llegada_counter = 0
        
        # Notificar a todos los clientes conectados
        if self.channel_layer:
            await self.channel_layer.group_send(
                "puente_grupo",
                {
                    "type": "reset_sistema"
                }
            )
            
            # Enviar estado limpio inmediatamente
            await self.channel_layer.group_send(
                "puente_grupo",
                {
                    "type": "estado_actualizado",
                    "estado": self.get_estado_puente()
                }
            )

    # Métodos para manejar eventos del grupo
    async def auto_registrado(self, event):
        await self.send(text_data=json.dumps({
            'type': 'auto_registrado',
            'auto': event['auto']
        }))

    async def auto_cruzando(self, event):
        await self.send(text_data=json.dumps({
            'type': 'auto_cruzando',
            'auto': event['auto']
        }))

    async def auto_salio(self, event):
        await self.send(text_data=json.dumps({
            'type': 'auto_salio',
            'auto': event['auto'],
            'eliminado': True
        }))

    async def auto_regreso_cola(self, event):
        await self.send(text_data=json.dumps({
            'type': 'auto_regreso_cola',
            'auto': event['auto']
        }))

    async def reset_sistema(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reset_sistema'
        }))
    
    async def estado_actualizado(self, event):
        await self.send(text_data=json.dumps({
            'type': 'estado_actualizado',
            'estado': event['estado']
        }))