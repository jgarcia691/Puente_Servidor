let socket;
let autosRegistrados = new Map();

// Conectar WebSocket
function conectarWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/puente/`;
    
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

// Manejar mensajes del servidor
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
        direccion: document.getElementById('direccionAuto').value
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
    agregarLog(`Auto ${auto.nombre} registrado (${auto.direccion === 'N' ? 'Norte a Sur' : 'Sur a Norte'})`, 'info');
    actualizarEstadisticas();
    
    // Iniciar simulación del auto
    iniciarSimulacionAuto(auto);
}

// Iniciar simulación de auto
function iniciarSimulacionAuto(auto) {
    const simularCruce = async () => {
        // Solicitar permiso para cruzar
        socket.send(JSON.stringify({
            type: 'solicitar_cruce',
            auto_id: auto.id
        }));
    };

    // Simular cruces repetidos
    const simularCiclo = () => {
        simularCruce();
        // Esperar tiempo aleatorio antes del siguiente cruce
        setTimeout(simularCiclo, (auto.tiempo_espera + Math.random() * 10) * 1000);
    };

    // Iniciar después de un delay inicial
    setTimeout(simularCiclo, Math.random() * 5000);
}

// Manejar respuesta de cruce
function manejarRespuestaCruce(respuesta) {
    if (respuesta.permiso) {
        agregarLog(`✅ ${respuesta.mensaje}`, 'success');
    } else {
        agregarLog(`⏳ ${respuesta.mensaje}`, 'warning');
    }
}

// Auto cruzando
function autoCruzando(auto) {
    agregarLog(`🚗 ${auto.nombre} está cruzando el puente`, 'info');
    actualizarEstadoPuente();
    
    // Simular tiempo de cruce basado en velocidad
    const tiempoCruce = (1000 / auto.velocidad) * 1000; // 1km a la velocidad del auto
    setTimeout(() => {
        socket.send(JSON.stringify({
            type: 'finalizar_cruce',
            auto_id: auto.id
        }));
    }, tiempoCruce);
}

// Auto salió del puente
function autoSalio(auto) {
    agregarLog(`✅ ${auto.nombre} ha salido del puente`, 'success');
    actualizarEstadoPuente();
}

// Generar autos aleatorios
function generarAutosAleatorios() {
    const cantidad = Math.floor(Math.random() * 5) + 3; // 3-7 autos
    agregarLog(`Generando ${cantidad} autos aleatorios...`, 'info');
    
    for (let i = 0; i < cantidad; i++) {
        setTimeout(() => {
            const autoData = {
                nombre: `Auto_${Math.floor(Math.random() * 9000) + 1000}`,
                velocidad: Math.random() * 50 + 30, // 30-80 km/h
                tiempo_espera: Math.random() * 15 + 5, // 5-20 segundos
                direccion: Math.random() > 0.5 ? 'N' : 'S'
            };
            
            socket.send(JSON.stringify({
                type: 'registrar_auto',
                auto: autoData
            }));
        }, i * 1000); // Espaciar registros por 1 segundo
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
                puenteStatus.textContent = `Puente Ocupado - ${data.autos_en_puente[0].nombre}`;
                puenteVisual.style.background = 'linear-gradient(90deg, #e74c3c 0%, #c0392b 50%, #e74c3c 100%)';
                document.getElementById('estadoPuente').textContent = 'Ocupado';
            } else {
                puenteStatus.textContent = 'Puente Libre';
                puenteVisual.style.background = 'linear-gradient(90deg, #27ae60 0%, #2ecc71 50%, #27ae60 100%)';
                document.getElementById('estadoPuente').textContent = 'Libre';
            }
        });
}

// Actualizar lista de autos
function actualizarListaAutos(elementId, autos) {
    const container = document.getElementById(elementId);
    if (autos.length === 0) {
        container.innerHTML = '<p>Ningún auto</p>';
        return;
    }
    
    container.innerHTML = autos.map(auto => 
        `<div class="auto-item ${auto.en_puente ? 'en-puente' : ''}">
            <strong>${auto.nombre}</strong><br>
            ${auto.direccion === 'N' ? 'Norte a Sur' : 'Sur a Norte'} - ${auto.velocidad} km/h
        </div>`
    ).join('');
}

// Actualizar estadísticas
function actualizarEstadisticas() {
    document.getElementById('totalAutos').textContent = autosRegistrados.size;
}

// Agregar entrada al log
function agregarLog(mensaje, tipo = 'info') {
    const logContainer = document.getElementById('logContainer');
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