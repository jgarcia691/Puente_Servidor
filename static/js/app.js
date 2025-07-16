let socket;
let autosRegistrados = new Map();
let autosCruzando = new Set();
let autosFinalizados = new Set();
let timeoutsFinalizar = new Map();
let autosEsperandoTurno = new Set();
let timeoutsSimulacion = new Map();
let intervalosSimulacion = new Map();

// Conectar WebSocket
function conectarWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/puente_app/`;

    console.log('Intentando conectar a:', wsUrl);
    
    try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log('WebSocket conectado exitosamente');
            agregarLog('Conexión establecida con el servidor', 'info');
        };

        socket.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                console.log('Mensaje recibido:', data);
                manejarMensaje(data);
            } catch (error) {
                console.error('Error al parsear mensaje:', error);
                agregarLog('Error al procesar mensaje del servidor', 'error');
            }
        };

        socket.onclose = (event) => {
            console.log('WebSocket cerrado:', event.code, event.reason);
            agregarLog(`Conexión cerrada (código: ${event.code})`, 'error');
            setTimeout(conectarWebSocket, 5000); // reconectar
        };

        socket.onerror = (error) => {
            console.error('Error en WebSocket:', error);
            agregarLog('Error en la conexión WebSocket', 'error');
        };
    } catch (error) {
        console.error('Error al crear WebSocket:', error);
        agregarLog('Error al crear conexión WebSocket', 'error');
        setTimeout(conectarWebSocket, 5000);
    }
}

function resetearSistema() {
    console.log('Reseteando sistema...');
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resetear_sistema' }));
        agregarLog('Solicitud de reset enviada al servidor', 'info');
    } else {
        agregarLog('No hay conexión activa para enviar reset', 'warning');
    }
    limpiarInterfazSistema();
}

function limpiarInterfazSistema() {
    const logContainer = document.getElementById('logContainer');
    if (logContainer) logContainer.innerHTML = '';
    actualizarListaAutos('autosEsperandoList', []);
    document.getElementById('totalAutos').textContent = '0';
    document.getElementById('estadoPuente').textContent = 'Libre';
    const puenteStatus = document.getElementById('puenteStatus');
    if (puenteStatus) puenteStatus.textContent = 'Puente Libre';

    autosRegistrados.clear();
    autosCruzando.clear();
    autosFinalizados.clear();
    autosEsperandoTurno.clear();

    timeoutsSimulacion.forEach(clearTimeout);
    timeoutsSimulacion.clear();
    timeoutsFinalizar.forEach(clearTimeout);
    timeoutsFinalizar.clear();
    intervalosSimulacion.forEach(clearInterval);
    intervalosSimulacion.clear();
}

function manejarMensaje(data) {
    console.log('Manejando mensaje:', data.type);
    
    try {
        switch (data.type) {
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
            case 'auto_regreso_cola':
                autoRegresoACola(data.auto);
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
            default:
                console.warn('Tipo de mensaje no reconocido:', data.type);
                break;
        }
    } catch (error) {
        console.error('Error al manejar mensaje:', error, data);
        agregarLog('Error al procesar mensaje del servidor', 'error');
    }
}

function actualizarEstadoInicial(estado) {
    actualizarListaAutos('autosEsperandoList', estado.autos_esperando);
    document.getElementById('totalAutos').textContent = estado.total_autos;

    const puenteStatus = document.getElementById('puenteStatus');
    const puenteVisual = document.getElementById('puenteVisual');
    const estadoPuente = document.getElementById('estadoPuente');

    if (estado.autos_en_puente && estado.autos_en_puente.length > 0) {
        const auto = estado.autos_en_puente[0];
        puenteStatus.textContent = `Puente Ocupado por: ${auto.nombre}`;
        puenteVisual.style.background = 'linear-gradient(90deg, #e74c3c 0%, #c0392b 50%, #e74c3c 100%)';
        estadoPuente.textContent = `Ocupado por: ${auto.nombre}`;
    } else {
        puenteStatus.textContent = 'Puente Libre';
        puenteVisual.style.background = 'linear-gradient(90deg, #27ae60 0%, #2ecc71 50%, #27ae60 100%)';
        estadoPuente.textContent = 'Libre';
    }
}

function actualizarListaAutos(elementId, autos) {
    const tbody = document.getElementById('autosEsperandoTablaBody');
    if (!tbody) return;

    if (autos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">Ningún auto esperando</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    autos.forEach((auto, index) => {
        const tr = document.createElement('tr');
        const ordenTexto = index === 0 ? '🟢 PRÓXIMO' : `#${index + 1}`;
        tr.innerHTML = `
            <td>${auto.nombre}</td>
            <td>${getPrioridadTexto(auto.prioridad)}</td>
            <td>${auto.direccion === 'N' ? 'Norte→Sur' : 'Sur→Norte'}</td>
            <td>${auto.vueltas || auto.vueltas_totales}</td>
            <td>${ordenTexto}</td>
        `;
        tbody.appendChild(tr);
    });
}

function registrarAuto() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        agregarLog('No hay conexión activa para registrar auto', 'error');
        return;
    }

    const autoData = {
        nombre: document.getElementById('nombreAuto').value || `Auto_${Math.floor(Math.random() * 9000) + 1000}`,
        velocidad: parseFloat(document.getElementById('velocidadAuto').value) || 60,
        tiempo_espera: parseFloat(document.getElementById('tiempoEspera').value) || 10,
        direccion: document.getElementById('direccionAuto').value || 'N',
        prioridad: parseInt(document.getElementById('prioridadAuto')?.value || 5),
        vueltas: parseInt(document.getElementById('vueltasAuto')?.value || 1)
    };

    console.log('Registrando auto:', autoData);
    
    try {
        socket.send(JSON.stringify({
            type: 'registrar_auto',
            auto: autoData
        }));
        agregarLog(`Enviando registro de auto: ${autoData.nombre}`, 'info');
        document.getElementById('nombreAuto').value = '';
    } catch (error) {
        console.error('Error al enviar registro de auto:', error);
        agregarLog('Error al enviar registro de auto', 'error');
    }
}

function autoRegistrado(auto) {
    autosRegistrados.set(auto.id, auto);
    const prioridadTexto = getPrioridadTexto(auto.prioridad);
    const vueltasTexto = auto.vueltas_totales > 1 ? ` (${auto.vueltas_totales} vueltas)` : '';
    agregarLog(`🚗 Auto #${auto.id} (${auto.nombre}) registrado - Prioridad: ${prioridadTexto} - ${auto.direccion === 'N' ? 'Norte→Sur' : 'Sur→Norte'}${vueltasTexto}`, 'info');
    iniciarSimulacionAuto(auto);
}

function getPrioridadTexto(prioridad) {
    switch (prioridad) {
        case 1: return 'P1 (Crítica)';
        case 2: return 'P2 (Alta)';
        case 3: return 'P3 (Media)';
        case 4: return 'P4 (Baja)';
        case 5: return 'P5 (Muy Baja)';
        default: return `P${prioridad}`;
    }
}

function iniciarSimulacionAuto(auto) {
    if (intervalosSimulacion.has(auto.id)) {
        clearInterval(intervalosSimulacion.get(auto.id));
        intervalosSimulacion.delete(auto.id);
    }

    const intentarCruce = () => {
        if (autosRegistrados.has(auto.id) && !autosFinalizados.has(auto.id)) {
            socket.send(JSON.stringify({
                type: 'solicitar_cruce',
                auto_id: auto.id
            }));
        }
    };

    intentarCruce();

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

function manejarRespuestaCruce(respuesta) {
    if (respuesta.permiso) {
        agregarLog(`✅ ${respuesta.mensaje}`, 'success');
        autosEsperandoTurno.delete(respuesta.auto_id);
        if (intervalosSimulacion.has(respuesta.auto_id)) {
            clearInterval(intervalosSimulacion.get(respuesta.auto_id));
            intervalosSimulacion.delete(respuesta.auto_id);
        }
    } else {
        if (respuesta.auto_id && autosRegistrados.has(respuesta.auto_id)) {
            const auto = autosRegistrados.get(respuesta.auto_id);
            const nombre = `#${auto.id} (${auto.nombre})`;
            const prioridadTexto = getPrioridadTexto(auto.prioridad);

            if (!autosEsperandoTurno.has(respuesta.auto_id)) {
                if (respuesta.mensaje.includes('Puente ocupado')) {
                    agregarLog(`⏳ ${nombre} - ${prioridadTexto} esperando - puente ocupado`, 'warning');
                } else {
                    agregarLog(`⏳ ${nombre} - ${prioridadTexto} está esperando su turno`, 'warning');
                }
                autosEsperandoTurno.add(respuesta.auto_id);
            }
        }
    }
}

function autoCruzando(auto) {
    const direccionTexto = auto.direccion === 'N' ? 'Norte→Sur' : 'Sur→Norte';
    const vueltaActual = auto.cruzadas ? auto.cruzadas + 1 : 1;
    const vueltasTexto = auto.vueltas_totales > 1 ? ` (vuelta ${vueltaActual}/${auto.vueltas_totales})` : '';

    agregarLog(`🚗 ${auto.nombre} cruzando ${direccionTexto}${vueltasTexto}`, 'info');

    const puenteStatus = document.getElementById('puenteStatus');
    const puenteVisual = document.getElementById('puenteVisual');
    const estadoPuente = document.getElementById('estadoPuente');
    if (puenteStatus && puenteVisual && estadoPuente) {
        puenteStatus.textContent = `Puente Ocupado por: ${auto.nombre}`;
        puenteVisual.style.background = 'linear-gradient(90deg, #e74c3c 0%, #c0392b 50%, #e74c3c 100%)';
        estadoPuente.textContent = `Ocupado por: ${auto.nombre}`;
    }

    const longitudPuente = 0.5;
    const tiempoCruce = (longitudPuente / auto.velocidad) * 3600 * 1000;

    setTimeout(() => {
        socket.send(JSON.stringify({
            type: 'finalizar_cruce',
            auto_id: auto.id
        }));
    }, tiempoCruce);
}

function autoRegresoACola(auto) {
    const direccionTexto = auto.direccion === 'N' ? 'Norte→Sur' : 'Sur→Norte';
    const vueltasRestantes = auto.vueltas;
    const prioridadTexto = getPrioridadTexto(auto.prioridad);

    agregarLog(`🔄 Auto #${auto.id} (${auto.nombre}) regresó a la cola al FINAL (FIFO) - ${direccionTexto} - ${vueltasRestantes} vuelta(s) restante(s) - ${prioridadTexto}`, 'info');
    autosRegistrados.set(auto.id, auto);
    autosEsperandoTurno.delete(auto.id);
    iniciarSimulacionAuto(auto);
}

function autoSalio(auto) {
    const prioridadTexto = getPrioridadTexto(auto.prioridad);
    agregarLog(`🏁 Auto #${auto.id} (${auto.nombre}) completó todas sus vueltas (${auto.vueltas_totales}) - ${prioridadTexto}`, 'success');

    autosRegistrados.delete(auto.id);
    autosCruzando.delete(auto.id);
    autosEsperandoTurno.delete(auto.id);
    autosFinalizados.add(auto.id);

    if (intervalosSimulacion.has(auto.id)) {
        clearInterval(intervalosSimulacion.get(auto.id));
        intervalosSimulacion.delete(auto.id);
    }
    if (timeoutsFinalizar.has(auto.id)) {
        clearTimeout(timeoutsFinalizar.get(auto.id));
        timeoutsFinalizar.delete(auto.id);
    }

    autosEsperandoTurno.clear();
}

function generarAutosAleatorios() {
    const cantidad = Math.floor(Math.random() * 5) + 3;
    agregarLog(`Generando ${cantidad} autos aleatorios...`, 'info');

    for (let i = 0; i < cantidad; i++) {
        setTimeout(() => {
            const prioridad = Math.floor(Math.random() * 5) + 1;
            const vueltas = Math.floor(Math.random() * 4) + 1;
            const nombre = `Auto_${Math.floor(Math.random() * 9000) + 1000}_P${prioridad}_${vueltas}V`;

            const autoData = {
                nombre,
                velocidad: Math.random() * 50 + 30,
                tiempo_espera: Math.random() * 2 + 1,
                direccion: Math.random() > 0.5 ? 'N' : 'S',
                prioridad,
                vueltas
            };

            socket.send(JSON.stringify({
                type: 'registrar_auto',
                auto: autoData
            }));
        }, i * 1000);
    }
}

function agregarLog(mensaje, tipo = 'info') {
    const logContainer = document.getElementById('logContainer');
    if (!logContainer) return;

    const p = document.createElement('p');
    p.className = `log-${tipo}`;
    p.textContent = mensaje;

    logContainer.insertBefore(p, logContainer.firstChild);
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando aplicación...');
    conectarWebSocket();
    
    // Agregar event listeners para botones
    const resetButton = document.getElementById('resetButton');
    if (resetButton) {
        resetButton.addEventListener('click', resetearSistema);
    }
    
    const generarButton = document.getElementById('generarButton');
    if (generarButton) {
        generarButton.addEventListener('click', generarAutosAleatorios);
    }
    
    agregarLog('Aplicación inicializada', 'info');
    
    // Función de prueba para verificar FIFO
    window.probarFIFO = function() {
        agregarLog('🧪 Iniciando prueba de FIFO...', 'info');
        
        // Registrar 3 autos con diferentes vueltas
        const autosPrueba = [
            { nombre: 'Auto_Test1', vueltas: 2, prioridad: 3 },
            { nombre: 'Auto_Test2', vueltas: 1, prioridad: 3 },
            { nombre: 'Auto_Test3', vueltas: 3, prioridad: 3 }
        ];
        
        autosPrueba.forEach((auto, index) => {
            setTimeout(() => {
                // Llenar el formulario
                document.getElementById('nombreAuto').value = auto.nombre;
                document.getElementById('vueltasAuto').value = auto.vueltas;
                document.getElementById('prioridadAuto').value = auto.prioridad;
                
                // Registrar el auto
                registrarAuto();
                agregarLog(`🧪 Registrado ${auto.nombre} con ${auto.vueltas} vueltas`, 'info');
            }, index * 2000); // Registrar cada 2 segundos
        });
    };
});
