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

```bash
daphne puente_server.asgi:application
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
