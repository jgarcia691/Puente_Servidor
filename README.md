# 🌉 Sistema Distribuido - Control de Puente de Una Vía

## Descripción del Proyecto

Este sistema implementa un control distribuido para gestionar el tráfico en un puente de una vía. Los automóviles (procesos cliente) se conectan remotamente al servidor y solicitan permiso para cruzar el puente, respetando las reglas de dirección y evitando colisiones.

## 🏗️ Arquitectura del Sistema

### Componentes Principales

1. **Servidor Django** - Gestiona el estado del puente y coordina los clientes
2. **Clientes WebSocket** - Simulan automóviles que solicitan cruzar el puente
3. **Interfaz Web** - Visualización en tiempo real del estado del sistema
4. **Base de Datos** - Almacena información de los autos y su estado

### Protocolos Utilizados

#### Capa de Transporte
- **WebSocket** (WS/WSS) - Para comunicación en tiempo real
- **HTTP/HTTPS** - Para operaciones REST API

#### Capa de Aplicación
- **JSON** - Formato de mensajes entre cliente y servidor
- **Django Channels** - Framework para manejo de WebSockets

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.8+
- pip

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd Server-Proyecto
```

2. **Crear entorno virtual**
```bash
python -m venv venv
```

3. **Activar entorno virtual**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Instalar dependencias**
```bash
pip install django channels daphne
```

5. **Aplicar migraciones**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Crear superusuario (opcional)**
```bash
python manage.py createsuperuser
```

## 🏃‍♂️ Ejecución del Sistema

### Iniciar el Servidor
```bash
python manage.py runserver
```

El sistema estará disponible en: `http://localhost:8000`

### Acceso a la Interfaz
- **Interfaz Principal**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin

## 🎮 Uso del Sistema

### Funcionalidades Principales

1. **Registro de Autos**
   - Nombre personalizado o automático
   - Velocidad configurable (30-120 km/h)
   - Tiempo de espera entre cruces (5-30 segundos)
   - Dirección de viaje (Norte a Sur / Sur a Norte)

2. **Control de Cruce**
   - Solicitud automática de permiso
   - Verificación de dirección del puente
   - Tiempo de cruce basado en velocidad
   - Simulación de cruces repetidos

3. **Generación Automática**
   - Creación de autos aleatorios
   - Parámetros automáticos
   - Simulación de tráfico real

### Interfaz de Usuario

#### Panel de Control
- **Estado del Puente**: Visualización en tiempo real
- **Formulario de Registro**: Crear autos manualmente
- **Botón de Generación**: Crear autos aleatorios

#### Monitoreo
- **Autos en el Puente**: Lista de vehículos cruzando
- **Autos Esperando**: Vehículos en cola
- **Estadísticas**: Total de autos y estado del puente
- **Registro de Actividad**: Log de eventos en tiempo real

## 🔧 Lógica de Control del Puente

### Reglas de Operación

1. **Una Vía**: Solo un auto puede cruzar a la vez
2. **Dirección Única**: Los autos deben ir en la misma dirección
3. **Cola de Espera**: Autos en dirección diferente esperan
4. **Tiempo de Cruce**: Basado en velocidad del vehículo

### Algoritmo de Control

```python
def solicitar_cruce(auto_id):
    auto = obtener_auto(auto_id)
    autos_en_puente = obtener_autos_en_puente()
    
    if autos_en_puente:
        auto_en_puente = autos_en_puente[0]
        if auto_en_puente.direccion != auto.direccion:
            return DENEGAR_PERMISO
        else:
            return PERMITIR_CRUCE
    else:
        return PERMITIR_CRUCE
```

## 📡 API Endpoints

### WebSocket
- **ws://localhost:8000/ws/puente/** - Conexión WebSocket principal

### REST API
- **POST /api/registrar-auto/** - Registrar nuevo auto
- **POST /api/solicitar-cruce/** - Solicitar permiso de cruce
- **POST /api/finalizar-cruce/** - Finalizar cruce
- **GET /api/estado-puente/** - Obtener estado actual

## 🗄️ Modelo de Datos

### Auto
```python
class Auto(models.Model):
    nombre = CharField(max_length=50)
    velocidad = FloatField()  # km/h
    tiempo_espera = FloatField()  # segundos
    direccion = CharField(choices=[('N', 'Norte a Sur'), ('S', 'Sur a Norte')])
    en_puente = BooleanField(default=False)
    timestamp = DateTimeField(auto_now=True)
```

## 🔄 Flujo de Comunicación

### Secuencia de Mensajes

1. **Conexión**: Cliente se conecta via WebSocket
2. **Registro**: Cliente envía datos del auto
3. **Solicitud**: Cliente solicita permiso para cruzar
4. **Respuesta**: Servidor autoriza o deniega
5. **Cruce**: Cliente simula tiempo de cruce
6. **Finalización**: Cliente notifica salida del puente

### Tipos de Mensajes

```json
// Registro de auto
{
    "type": "registrar_auto",
    "auto": {
        "nombre": "Auto_1234",
        "velocidad": 60,
        "tiempo_espera": 10,
        "direccion": "N"
    }
}

// Solicitud de cruce
{
    "type": "solicitar_cruce",
    "auto_id": 1
}

// Respuesta del servidor
{
    "type": "respuesta_cruce",
    "data": {
        "success": true,
        "permiso": true,
        "mensaje": "Auto puede cruzar"
    }
}
```

## 🎯 Características del Sistema Distribuido

### Escalabilidad
- Múltiples clientes simultáneos
- Comunicación asíncrona
- Gestión de estado centralizada

### Concurrencia
- Manejo de múltiples conexiones WebSocket
- Control de acceso al recurso compartido (puente)
- Prevención de condiciones de carrera

### Tolerancia a Fallos
- Reconexión automática de clientes
- Persistencia de estado en base de datos
- Logging de eventos para debugging

## 🧪 Simulación y Testing

### Escenarios de Prueba

1. **Cruce Simple**: Un auto cruza sin interferencia
2. **Colisión de Direcciones**: Autos en direcciones opuestas
3. **Múltiples Autos**: Varios autos en la misma dirección
4. **Desconexión**: Cliente se desconecta durante cruce
5. **Carga Alta**: Muchos autos simultáneos

### Métricas de Rendimiento
- Tiempo de respuesta del servidor
- Número de autos manejados simultáneamente
- Eficiencia del control de tráfico
- Uso de recursos del sistema

## 🔍 Monitoreo y Debugging

### Logs del Sistema
- Conexiones de clientes
- Solicitudes de cruce
- Cambios de estado del puente
- Errores y excepciones

### Herramientas de Debugging
- Interfaz web en tiempo real
- Logs de actividad
- Estado de la base de datos
- Métricas de rendimiento

## 🚀 Mejoras Futuras

### Funcionalidades Adicionales
- [ ] Prioridad de vehículos (emergencias)
- [ ] Límites de velocidad variables
- [ ] Estadísticas avanzadas
- [ ] Notificaciones push
- [ ] API REST completa

### Optimizaciones
- [ ] Cache de estado del puente
- [ ] Compresión de mensajes
- [ ] Balanceo de carga
- [ ] Base de datos optimizada

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

## 👥 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📞 Soporte

Para soporte técnico o preguntas sobre el proyecto, contacta al equipo de desarrollo. 