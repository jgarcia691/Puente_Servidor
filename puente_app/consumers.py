import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Auto

class PuenteConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Unirse al grupo del puente
        await self.channel_layer.group_add("puente_grupo", self.channel_name)
        await self.accept()
        
        # Enviar estado inicial del puente
        estado = await self.get_estado_puente()
        await self.send(text_data=json.dumps({
            'type': 'estado_inicial',
            'data': estado
        }))

    async def disconnect(self, close_code):
        # Salir del grupo del puente
        await self.channel_layer.group_discard("puente_grupo", self.channel_name)

    async def receive(self, text_data):
        """Recibir mensajes de los clientes"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'registrar_auto':
                await self.handle_registrar_auto(data)
            elif message_type == 'solicitar_cruce':
                await self.handle_solicitar_cruce(data)
            elif message_type == 'finalizar_cruce':
                await self.handle_finalizar_cruce(data)
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

    async def handle_registrar_auto(self, data):
        """Manejar registro de nuevo auto"""
        auto_data = data.get('auto', {})
        auto = await self.crear_auto(auto_data)
        
        # Notificar a todos los clientes
        await self.channel_layer.group_send(
            "puente_grupo",
            {
                "type": "auto_registrado",
                "auto": {
                    "id": auto.id,
                    "direccion": auto.direccion,
                    "velocidad": round(auto.velocidad, 2),
                    "turno": auto.turno,
                    "tiempo_cruce": round(auto.tiempo_cruce, 2),
                    "tiempo_espera": round(auto.tiempo_espera, 2)
                }
            }
        )

    async def handle_solicitar_cruce(self, data):
        """Manejar solicitud de cruce"""
        auto_id = data.get('auto_id')
        resultado = await self.procesar_solicitud_cruce(auto_id)
        
        if resultado['permiso']:
            # Notificar a todos los clientes
            await self.channel_layer.group_send(
                "puente_grupo",
                {
                    "type": "auto_cruzando",
                    "auto": resultado['auto']
                }
            )
        
        # Enviar respuesta al cliente que solicitó
        await self.send(text_data=json.dumps({
            'type': 'respuesta_cruce',
            'data': resultado
        }))

    async def handle_finalizar_cruce(self, data):
        """Manejar finalización de cruce"""
        auto_id = data.get('auto_id')
        resultado = await self.procesar_finalizar_cruce(auto_id)
        
        if resultado['success']:
            # Notificar a todos los clientes
            await self.channel_layer.group_send(
                "puente_grupo",
                {
                    "type": "auto_salio",
                    "auto": resultado['auto']
                }
            )

    # Métodos de base de datos
    @database_sync_to_async
    def get_estado_puente(self):
        """Obtener estado actual del puente y serializar los autos según la nueva lógica de turnos y colas"""
        auto_norte = Auto.objects.filter(direccion='N').order_by('turno').first()
        auto_sur = Auto.objects.filter(direccion='S').order_by('turno').first()
        cola_norte = list(Auto.objects.filter(direccion='N', turno__gt=1).order_by('turno').values('id', 'turno', 'velocidad', 'tiempo_cruce', 'tiempo_espera'))
        cola_sur = list(Auto.objects.filter(direccion='S', turno__gt=1).order_by('turno').values('id', 'turno', 'velocidad', 'tiempo_cruce', 'tiempo_espera'))
        def serializar_auto(auto):
            return {
                'id': auto.id,
                'turno': auto.turno,
                'velocidad': round(auto.velocidad, 2),
                'tiempo_cruce': round(auto.tiempo_cruce, 2),
                'tiempo_espera': round(auto.tiempo_espera, 2),
                'direccion': auto.direccion,
                'timestamp': auto.timestamp.isoformat() if auto.timestamp else None
            }
        return {
            'cruzando_norte': serializar_auto(auto_norte) if auto_norte else None,
            'cruzando_sur': serializar_auto(auto_sur) if auto_sur else None,
            'cola_norte': cola_norte,
            'cola_sur': cola_sur
        }

    @database_sync_to_async
    def crear_auto(self, auto_data):
        """Crear un nuevo auto en la base de datos con lógica de turnos y tiempos"""
        import random
        LONGITUD_PUENTE = 500
        direccion = random.choice(['N', 'S'])
        velocidad = random.uniform(20, 60)
        cola = Auto.objects.filter(direccion=direccion).order_by('turno')
        turno = cola.count() + 1
        velocidad_m_s = velocidad * 1000 / 3600
        tiempo_cruce = LONGITUD_PUENTE / velocidad_m_s
        tiempo_espera = sum([a.tiempo_cruce for a in cola])
        return Auto.objects.create(
            direccion=direccion,
            velocidad=velocidad,
            turno=turno,
            tiempo_cruce=tiempo_cruce,
            tiempo_espera=tiempo_espera
        )

    @database_sync_to_async
    def procesar_solicitud_cruce(self, auto_id):
        """Permitir el cruce solo al auto con turno 1 en su cola"""
        try:
            auto = Auto.objects.get(id=auto_id)
            primero = Auto.objects.filter(direccion=auto.direccion).order_by('turno').first()
            if primero and primero.id == auto.id:
                return {
                    'success': True,
                    'permiso': True,
                    'mensaje': f'Auto {auto.id} puede cruzar el puente',
                    'auto': {
                        'id': auto.id,
                        'direccion': auto.direccion,
                        'velocidad': round(auto.velocidad, 2),
                        'turno': auto.turno,
                        'tiempo_cruce': round(auto.tiempo_cruce, 2),
                        'tiempo_espera': round(auto.tiempo_espera, 2)
                    }
                }
            else:
                return {
                    'success': False,
                    'permiso': False,
                    'mensaje': 'No es tu turno para cruzar el puente.'
                }
        except Auto.DoesNotExist:
            return {
                'success': False,
                'permiso': False,
                'mensaje': 'Auto no encontrado'
            }

    @database_sync_to_async
    def procesar_finalizar_cruce(self, auto_id):
        """Eliminar el auto que cruzó y actualizar turnos y tiempos de espera de la cola"""
        try:
            auto = Auto.objects.get(id=auto_id)
            direccion = auto.direccion
            auto_data = {
                'id': auto.id,
                'direccion': auto.direccion
            }
            auto.delete()
            # Actualizar turnos y tiempos de espera de los autos restantes en la cola
            LONGITUD_PUENTE = 500
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
            return {
                'success': True,
                'mensaje': f'Auto {auto_data["id"]} ha salido del puente y fue eliminado',
                'auto': auto_data
            }
        except Auto.DoesNotExist:
            return {
                'success': False,
                'mensaje': 'Auto no encontrado'
            }

    # Métodos para manejar mensajes del grupo
    async def auto_registrado(self, event):
        """Enviar notificación de auto registrado"""
        await self.send(text_data=json.dumps({
            'type': 'auto_registrado',
            'auto': event['auto']
        }))

    async def auto_cruzando(self, event):
        """Enviar notificación de auto cruzando"""
        await self.send(text_data=json.dumps({
            'type': 'auto_cruzando',
            'auto': event['auto']
        }))

    async def auto_salio(self, event):
        """Enviar notificación de auto que salió y fue eliminado"""
        await self.send(text_data=json.dumps({
            'type': 'auto_salio',
            'auto': event['auto'],
            'eliminado': True
        })) 