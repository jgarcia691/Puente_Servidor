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
        await self.channel_layer.group_add("puente_grupo", self.channel_name)
        await self.accept()
        estado = self.get_estado_puente()
        await self.send(text_data=json.dumps({
            'type': 'estado_inicial',
            'data': estado
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("puente_grupo", self.channel_name)

    async def receive(self, text_data):
        try:
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

    def get_estado_puente(self):
        auto_en_puente = [PuenteConsumer.autos[PuenteConsumer.autos_en_puente]] if PuenteConsumer.autos_en_puente else []
        cola_ordenada = sorted(PuenteConsumer.cola_espera)
        autos_esperando = [PuenteConsumer.autos[aid] for (_, _, aid) in cola_ordenada if aid in PuenteConsumer.autos]
        return {
            'autos_en_puente': auto_en_puente,
            'autos_esperando': autos_esperando,
            'total_autos': len(PuenteConsumer.autos)
        }

    async def handle_registrar_auto(self, data):
        auto_data = data.get('auto', {})
        auto_id = PuenteConsumer.auto_id_counter
        PuenteConsumer.auto_id_counter += 1
        prioridad = auto_data.get('prioridad', 3)
        llegada = PuenteConsumer.llegada_counter
        PuenteConsumer.llegada_counter += 1
        
        auto = {
            'id': auto_id,
            'nombre': auto_data.get('nombre', f'Auto_{auto_id}'),
            'velocidad': auto_data.get('velocidad', 60),
            'tiempo_espera': auto_data.get('tiempo_espera', 10),
            'direccion': auto_data.get('direccion', 'N'),
            'prioridad': prioridad,
            'en_puente': False,
            'llegada': llegada  # Guardar orden de llegada
        }
        
        PuenteConsumer.autos[auto_id] = auto
        heappush(PuenteConsumer.cola_espera, (prioridad, llegada, auto_id))
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

    async def handle_solicitar_cruce(self, data):
        auto_id = data.get('auto_id')
        
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

    async def handle_finalizar_cruce(self, data):
        auto_id = data.get('auto_id')
        
        if PuenteConsumer.autos_en_puente == auto_id:
            PuenteConsumer.autos_en_puente = None
            auto = PuenteConsumer.autos.pop(auto_id, None)
            
            if auto:
                await self.channel_layer.group_send(
                    "puente_grupo",
                    {
                        "type": "auto_salio",
                        "auto": auto,
                        "eliminado": True
                    }
                )
            
            # Notificar a todos los clientes el estado actualizado
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

    async def reset_sistema(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reset_sistema'
        }))
    
    async def estado_actualizado(self, event):
        await self.send(text_data=json.dumps({
            'type': 'estado_actualizado',
            'estado': event['estado']
        }))