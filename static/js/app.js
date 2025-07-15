let socket;
let autosRegistrados = new Map();
let autosCruzando = new Set();
let autosFinalizados = new Set();
let timeoutsFinalizar = new Map();
let autosEsperandoTurno = new Set(); // IDs de autos que ya están esperando su turno
let timeoutsSimulacion = new Map(); // Para limpiar timeouts al resetear
let intervalosSimulacion = new Map(); // Para intervalos continuos

// Conectar WebSocket
function conectarWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/puente_app/`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function(e) {
        agregarLog('Conexión establecida con el servidor', 'info');
    };
    
    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        manejarMensaje(data);
    };
    
    socket.onclose = function(e) {
        agregarLog('Conexión cerrada', 'error');
        // Reintentar conexión después de 5 segundos
        setTimeout(conectarWebSocket, 5000);
    };
    
    socket.onerror = function(e) {
        agregarLog('Error en la conexión WebSocket', 'error');
    };
}

function resetearSistema() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resetear_sistema' }));
    }
    // Limpia el log y los estados locales inmediatamente
    limpiarInterfazSistema();
}

function limpiarInterfazSistema() {
    // Limpiar logs
    const logContainer = document.getElementById('logContainer');
    if (logContainer) logContainer.innerHTML = '';
    // Limpiar listas
    actualizarListaAutos('autosEnPuenteList', []);
    actualizarListaAutos('autosEsperandoList', []);
    document.getElementById('totalAutos').textContent = '0';
    document.getElementById('estadoPuente').textContent = 'Libre';
    const puenteStatus = document.getElementById('puenteStatus');
    if (puenteStatus) puenteStatus.textContent = 'Puente Libre';
    
    // Limpiar estados locales
    autosRegistrados.clear();
    autosCruzando.clear();
    autosFinalizados.clear();
    autosEsperandoTurno.clear();
    
    // Limpiar todos los timeouts e intervalos
    timeoutsSimulacion.forEach(timeout => clearTimeout(timeout));
    timeoutsSimulacion.clear();
    timeoutsFinalizar.forEach(timeout => clearTimeout(timeout));
    timeoutsFinalizar.clear();
    intervalosSimulacion.forEach(interval => clearInterval(interval));
    intervalosSimulacion.clear();
}

// Escuchar notificación de reseteo desde el backend
function manejarMensaje(data) {
    switch(data.type) {
        case 'estado_inicial':
            actualizarEstadoInicial(data.data);
            break;
        case 'auto_registrado':
            autoRegistrado(data.auto);
            break;
        case 'auto_cruzando':
            autoCruzando(data.auto);
            break;
        case 'auto_salio':
            autoSalio(data.auto);
            break;
        case 'respuesta_cruce':
            manejarRespuestaCruce(data.data);
            break;
        case 'reset_sistema':
            limpiarInterfazSistema();
            agregarLog('🔄 Sistema reseteado', 'info');
            break;
        case 'estado_actualizado':
            actualizarEstadoInicial(data.estado);
            break;
        case 'error':
            agregarLog(`Error: ${data.message}`, 'error');
            break;
    }
}

// Actualizar estado inicial
function actualizarEstadoInicial(estado) {
    actualizarListaAutos('autosEnPuenteList', estado.autos_en_puente);
    actualizarListaAutos('autosEsperandoList', estado.autos_esperando);
    document.getElementById('totalAutos').textContent = estado.total_autos;
    actualizarEstadoPuente();
}

// Registrar nuevo auto
function registrarAuto() {
    const autoData = {
        nombre: document.getElementById('nombreAuto').value || `Auto_${Math.floor(Math.random() * 9000) + 1000}`,
        velocidad: parseFloat(document.getElementById('velocidadAuto').value),
        tiempo_espera: parseFloat(document.getElementById('tiempoEspera').value),
        direccion: document.getElementById('direccionAuto').value,
        prioridad: parseInt(document.getElementById('prioridadAuto').value) || 3
    };

    socket.send(JSON.stringify({
        type: 'registrar_auto',
        auto: autoData
    }));

    // Limpiar formulario
    document.getElementById('nombreAuto').value = '';
}

// Auto registrado
function autoRegistrado(auto) {
    autosRegistrados.set(auto.id, auto);
    const prioridadTexto = getPrioridadTexto(auto.prioridad);
    agregarLog(`Auto #${auto.id} (${auto.nombre}) registrado - Prioridad: ${prioridadTexto} (${auto.direccion === 'N' ? 'Norte a Sur' : 'Sur a Norte'})`, 'info');
    actualizarEstadisticas();
    // Iniciar simulación del auto inmediatamente
    iniciarSimulacionAuto(auto);
}

// Función para obtener texto de prioridad
function getPrioridadTexto(prioridad) {
    switch(prioridad) {
        case 1: return 'P1 (Crítica)';
        case 2: return 'P2 (Alta)';
        case 3: return 'P3 (Media)';
        case 4: return 'P4 (Baja)';
        case 5: return 'P5 (Muy Baja)';
        default: return `P${prioridad}`;
    }
}

// Función para obtener color de prioridad
function getColorPrioridad(prioridad) {
    switch(prioridad) {
        case 1: return '#e74c3c'; // Rojo - Crítica
        case 2: return '#f39c12'; // Naranja - Alta
        case 3: return '#f1c40f'; // Amarillo - Media
        case 4: return '#3498db'; // Azul - Baja
        case 5: return '#95a5a6'; // Gris - Muy Baja
        default: return '#34495e'; // Gris oscuro
    }
}

// Iniciar simulación de auto - CORREGIDO
function iniciarSimulacionAuto(auto) {
    // Si ya hay un intervalo para este auto, no lo dupliques
    if (intervalosSimulacion.has(auto.id)) return;
    
    const intentarCruce = () => {
        // Solo intentar si el auto aún está registrado y no ha terminado
        if (autosRegistrados.has(auto.id) && !autosFinalizados.has(auto.id)) {
            socket.send(JSON.stringify({
                type: 'solicitar_cruce',
                auto_id: auto.id
            }));
        }
    };
    
    // Primer intento inmediato
    intentarCruce();
    
    // Configurar intervalos regulares para reintentos
    const intervalo = setInterval(() => {
        if (!autosRegistrados.has(auto.id) || autosFinalizados.has(auto.id)) {
            clearInterval(intervalo);
            intervalosSimulacion.delete(auto.id);
            return;
        }
        intentarCruce();
    }, (auto.tiempo_espera + Math.random() * 5) * 1000);
    
    intervalosSimulacion.set(auto.id, intervalo);
}

// Manejar respuesta de cruce
function manejarRespuestaCruce(respuesta) {
    if (respuesta.permiso) {
        agregarLog(`✅ ${respuesta.mensaje}`, 'success');
        autosEsperandoTurno.delete(respuesta.auto_id);
        // Detener la simulación para este auto ya que está cruzando
        if (intervalosSimulacion.has(respuesta.auto_id)) {
            clearInterval(intervalosSimulacion.get(respuesta.auto_id));
            intervalosSimulacion.delete(respuesta.auto_id);
        }
    } else {
        let nombre = '';
        let prioridadTexto = '';
        if (respuesta.auto_id && autosRegistrados.has(respuesta.auto_id)) {
            const auto = autosRegistrados.get(respuesta.auto_id);
            nombre = `#${auto.id} (${auto.nombre})`;
            prioridadTexto = getPrioridadTexto(auto.prioridad);
        }
        
        // Solo mostrar mensaje de espera la primera vez
        if (respuesta.mensaje === 'No es el turno de este auto para cruzar' && nombre) {
            if (!autosEsperandoTurno.has(respuesta.auto_id)) {
                agregarLog(`⏳ ${nombre} - ${prioridadTexto} está esperando su turno`, 'warning');
                autosEsperandoTurno.add(respuesta.auto_id);
            }
        } else if (respuesta.mensaje.includes('Puente ocupado')) {
            if (!autosEsperandoTurno.has(respuesta.auto_id)) {
                agregarLog(`⏳ ${nombre} - ${prioridadTexto} esperando - puente ocupado`, 'warning');
                autosEsperandoTurno.add(respuesta.auto_id);
            }
        }
    }
}

// Auto cruzando
function autoCruzando(auto) {
    const prioridadTexto = getPrioridadTexto(auto.prioridad);
    agregarLog(`🚗 Auto #${auto.id} (${auto.nombre}) - ${prioridadTexto} está cruzando el puente`, 'info');
    autosCruzando.add(auto.id);
    actualizarEstadoPuente();
    
    // Si ya se finalizó el cruce para este auto, no volver a programar
    if (autosFinalizados.has(auto.id)) return;
    // Si ya hay un timeout programado para este auto, no hacer nada
    if (timeoutsFinalizar.has(auto.id)) return;
    
    const tiempoCruce = (1000 / auto.velocidad) * 1000;
    const timeoutId = setTimeout(() => {
        if (!autosFinalizados.has(auto.id)) {
            socket.send(JSON.stringify({
                type: 'finalizar_cruce',
                auto_id: auto.id
            }));
            autosFinalizados.add(auto.id);
        }
        timeoutsFinalizar.delete(auto.id);
    }, tiempoCruce);
    
    timeoutsFinalizar.set(auto.id, timeoutId);
}

// Auto salió del puente - CORREGIDO
function autoSalio(auto) {
    const prioridadTexto = getPrioridadTexto(auto.prioridad);
    agregarLog(`✅ Auto #${auto.id} (${auto.nombre}) - ${prioridadTexto} ha salido del puente`, 'success');
    
    // Limpiar estados del auto que salió
    autosRegistrados.delete(auto.id);
    autosCruzando.delete(auto.id);
    autosEsperandoTurno.delete(auto.id);
    
    // Limpiar intervalos y timeouts
    if (intervalosSimulacion.has(auto.id)) {
        clearInterval(intervalosSimulacion.get(auto.id));
        intervalosSimulacion.delete(auto.id);
    }
    if (timeoutsFinalizar.has(auto.id)) {
        clearTimeout(timeoutsFinalizar.get(auto.id));
        timeoutsFinalizar.delete(auto.id);
    }
    
    actualizarEstadoPuente();
    
    // Limpiar el set de autos esperando turno para que vuelvan a mostrar mensajes
    autosEsperandoTurno.clear();
    
    // Los autos que siguen en el sistema continuarán intentando
    // gracias a sus intervalos individuales
}

// Generar autos aleatorios
function generarAutosAleatorios() {
    const cantidad = 5;
    agregarLog(`Generando ${cantidad} autos aleatorios...`, 'info');
    
    for (let i = 0; i < cantidad; i++) {
        setTimeout(() => {
            // Generar prioridad aleatoria con distribución más realista
            const prioridadRandom = Math.random();
            let prioridad;
            if (prioridadRandom < 0.1) prioridad = 1;      // 10% prioridad crítica
            else if (prioridadRandom < 0.25) prioridad = 2; // 15% prioridad alta
            else if (prioridadRandom < 0.60) prioridad = 3; // 35% prioridad media
            else if (prioridadRandom < 0.85) prioridad = 4; // 25% prioridad baja
            else prioridad = 5;                             // 15% prioridad muy baja

            const autoData = {
                nombre: `Auto_${Math.floor(Math.random() * 9000) + 1000}`,
                velocidad: Math.random() * 50 + 30, // 30-80 km/h
                tiempo_espera: Math.random() * 10 + 5, // 5-15 segundos
                direccion: Math.random() > 0.5 ? 'N' : 'S',
                prioridad: prioridad
            };
            
            socket.send(JSON.stringify({
                type: 'registrar_auto',
                auto: autoData
            }));
        }, i * 500); // Espaciar registros por 0.5 segundos
    }
}

// Actualizar estado del puente
function actualizarEstadoPuente() {
    fetch('/api/estado-puente/')
        .then(response => response.json())
        .then(data => {
            actualizarListaAutos('autosEnPuenteList', data.autos_en_puente);
            actualizarListaAutos('autosEsperandoList', data.autos_esperando);
            document.getElementById('totalAutos').textContent = data.total_autos;
            
            const puenteStatus = document.getElementById('puenteStatus');
            const puenteVisual = document.getElementById('puenteVisual');
            
            if (data.autos_en_puente.length > 0) {
                const auto = data.autos_en_puente[0];
                const prioridadTexto = getPrioridadTexto(auto.prioridad);
                puenteStatus.textContent = `Puente Ocupado - Auto #${auto.id} (${auto.nombre}) - ${prioridadTexto}`;
                puenteVisual.style.background = 'linear-gradient(90deg, #e74c3c 0%, #c0392b 50%, #e74c3c 100%)';
                document.getElementById('estadoPuente').textContent = 'Ocupado';
            } else {
                puenteStatus.textContent = 'Puente Libre';
                puenteVisual.style.background = 'linear-gradient(90deg, #27ae60 0%, #2ecc71 50%, #27ae60 100%)';
                document.getElementById('estadoPuente').textContent = 'Libre';
            }
        })
        .catch(error => {
            console.error('Error al actualizar estado del puente:', error);
        });
}

// Actualizar lista de autos
function actualizarListaAutos(elementId, autos) {
    const container = document.getElementById(elementId);
    if (!container) return;
    
    if (autos.length === 0) {
        container.innerHTML = '<p>Ningún auto</p>';
        return;
    }
    
    container.innerHTML = autos.map(auto => {
        const prioridadTexto = getPrioridadTexto(auto.prioridad);
        const colorPrioridad = getColorPrioridad(auto.prioridad);
        return `<div class="auto-item ${auto.en_puente ? 'en-puente' : ''}">
            <strong>#${auto.id} - ${auto.nombre}</strong>
            <span class="prioridad-badge" style="background-color: ${colorPrioridad}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px;">${prioridadTexto}</span><br>
            ${auto.direccion === 'N' ? 'Norte a Sur' : 'Sur a Norte'} - ${auto.velocidad.toFixed(1)} km/h
        </div>`;
    }).join('');
}

// Actualizar estadísticas
function actualizarEstadisticas() {
    document.getElementById('totalAutos').textContent = autosRegistrados.size;
}

// Agregar entrada al log
function agregarLog(mensaje, tipo = 'info') {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    let icon = 'ℹ️';
    if (tipo === 'error') icon = '❌';
    else if (tipo === 'success') icon = '✅';
    else if (tipo === 'warning') icon = '⚠️';
    
    logEntry.innerHTML = `
        <span class="timestamp">${timestamp}</span>
        ${icon} ${mensaje}
    `;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Inicializar cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    conectarWebSocket();
    agregarLog('Sistema de control del puente iniciado', 'info');
});