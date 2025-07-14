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
                    "nombre": auto.nombre,
                    "direccion": auto.direccion,
                    "velocidad": auto.velocidad,
                    "tiempo_espera": auto.tiempo_espera
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
        """Obtener estado actual del puente y serializar datetime a string"""
        autos_en_puente = Auto.objects.filter(en_puente=True)
        autos_esperando = Auto.objects.filter(en_puente=False)

        def serializar_auto(auto):
            return {
                'id': auto.id,
                'nombre': auto.nombre,
                'velocidad': auto.velocidad,
                'tiempo_espera': auto.tiempo_espera,
                'direccion': auto.direccion,
                'en_puente': auto.en_puente,
                'timestamp': auto.timestamp.isoformat() if auto.timestamp else None
            }

        return {
            'autos_en_puente': [serializar_auto(a) for a in autos_en_puente],
            'autos_esperando': [serializar_auto(a) for a in autos_esperando],
            'total_autos': Auto.objects.count()
        }

    @database_sync_to_async
    def crear_auto(self, auto_data):
        """Crear un nuevo auto en la base de datos"""
        import random
        return Auto.objects.create(
            nombre=auto_data.get('nombre', f'Auto_{random.randint(1000, 9999)}'),
            velocidad=auto_data.get('velocidad', random.uniform(30, 80)),
            tiempo_espera=auto_data.get('tiempo_espera', random.uniform(5, 15)),
            direccion=auto_data.get('direccion', random.choice(['N', 'S']))
        )

    @database_sync_to_async
    def procesar_solicitud_cruce(self, auto_id):
        """Procesar solicitud de cruce del puente"""
        try:
            auto = Auto.objects.get(id=auto_id)
            autos_en_puente = Auto.objects.filter(en_puente=True)
            
            if autos_en_puente.exists():
                auto_en_puente = autos_en_puente.first()
                if auto_en_puente.direccion != auto.direccion:
                    return {
                        'success': False,
                        'permiso': False,
                        'mensaje': f'Puente ocupado por auto en dirección {auto_en_puente.get_direccion_display()}'
                    }
            
            # Dar permiso para cruzar
            auto.en_puente = True
            auto.save()
            
            return {
                'success': True,
                'permiso': True,
                'mensaje': f'Auto {auto.nombre} puede cruzar el puente',
                'auto': {
                    'id': auto.id,
                    'nombre': auto.nombre,
                    'direccion': auto.direccion
                }
            }
        except Auto.DoesNotExist:
            return {
                'success': False,
                'permiso': False,
                'mensaje': 'Auto no encontrado'
            }

    @database_sync_to_async
    def procesar_finalizar_cruce(self, auto_id):
        """Procesar finalización de cruce y eliminar el auto"""
        try:
            auto = Auto.objects.get(id=auto_id)
            auto_data = {
                'id': auto.id,
                'nombre': auto.nombre,
                'direccion': auto.direccion
            }
            auto.delete()  # Eliminar el auto de la base de datos
            return {
                'success': True,
                'mensaje': f'Auto {auto_data["nombre"]} ha salido del puente y fue eliminado',
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