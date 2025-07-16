let socket;
let autosEnPuente = [];
let autosEsperandoNorte = [];
let autosEsperandoSur = [];
let simulacionIniciada = false;
let autosSimulando = new Set();

function conectarWebSocketDashboard() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/puente_app/`;
    
    console.log('Dashboard: Conectando a WebSocket:', wsUrl);
    
    try {
        socket = new WebSocket(wsUrl);
        socket.onopen = function() {
            console.log('Dashboard: WebSocket conectado');
            actualizarDashboardEstado('Conectado');
        };
        socket.onmessage = function(e) {
            try {
                const data = JSON.parse(e.data);
                console.log('Dashboard: Mensaje recibido:', data.type);
                manejarMensajeDashboard(data);
            } catch (error) {
                console.error('Dashboard: Error al parsear mensaje:', error);
            }
        };
        socket.onclose = function(event) {
            console.log('Dashboard: WebSocket cerrado:', event.code);
            actualizarDashboardEstado('Desconectado');
            setTimeout(conectarWebSocketDashboard, 5000);
        };
        socket.onerror = function(error) {
            console.error('Dashboard: Error en WebSocket:', error);
            actualizarDashboardEstado('Error de conexión');
        };
    } catch (error) {
        console.error('Dashboard: Error al crear WebSocket:', error);
        actualizarDashboardEstado('Error al conectar');
    }
}

function manejarMensajeDashboard(data) {
    try {
        switch (data.type) {
            case 'estado_inicial':
            case 'estado_actualizado':
                renderizarDashboard(data.data || data.estado);
                break;
            case 'auto_registrado':
                console.log('Dashboard: Auto registrado:', data.auto.nombre);
                break;
            case 'auto_cruzando':
                console.log('Dashboard: Auto cruzando:', data.auto.nombre);
                break;
            case 'auto_salio':
                console.log('Dashboard: Auto completó todas las vueltas:', data.auto.nombre);
                break;
            case 'auto_regreso_cola':
                console.log('Dashboard: Auto regresó a la cola (FIFO):', data.auto.nombre);
                break;
            case 'reset_sistema':
                console.log('Dashboard: Sistema reseteado');
                // Limpiar el dashboard
                document.getElementById('autosEnPuente').innerHTML = '';
                document.getElementById('colaNorte').innerHTML = '';
                document.getElementById('colaSur').innerHTML = '';
                document.getElementById('dashboardTotal').textContent = 'Total de Autos: 0';
                document.getElementById('dashboardEstado').textContent = 'Estado: Libre';
                break;
            case 'error':
                console.error('Dashboard: Error del servidor:', data.message);
                break;
            default:
                console.log('Dashboard: Mensaje no manejado:', data.type);
        }
    } catch (error) {
        console.error('Dashboard: Error al manejar mensaje:', error);
    }
}

function renderizarDashboard(estado) {
    // Autos cruzando
    autosEnPuente = estado.autos_en_puente || [];
    // Autos esperando
    autosEsperandoNorte = (estado.autos_esperando || []).filter(a => a.direccion === 'N');
    autosEsperandoSur = (estado.autos_esperando || []).filter(a => a.direccion === 'S');

    // Renderizar autos en el puente
    const puenteDiv = document.getElementById('autosEnPuente');
    puenteDiv.innerHTML = '';
    autosEnPuente.forEach(auto => {
        const autoDiv = document.createElement('div');
        autoDiv.className = `auto-dashboard ${auto.direccion === 'N' ? 'norte' : 'sur'}`;
        autoDiv.innerHTML = `<span>${auto.nombre}</span><span>P${auto.prioridad} | V${auto.vueltas || 1} | L${auto.llegada}</span>`;
        autoDiv.style.transform = auto.direccion === 'N' ? 'translateX(250px)' : 'translateX(0)';
        puenteDiv.appendChild(autoDiv);
    });

    // Renderizar autos esperando norte
    const colaNorteDiv = document.getElementById('colaNorte');
    colaNorteDiv.innerHTML = '';
    autosEsperandoNorte.forEach((auto, index) => {
        const autoDiv = document.createElement('div');
        autoDiv.className = 'auto-dashboard norte';
        const ordenTexto = index === 0 ? '🟢 PRÓXIMO' : `#${index + 1}`;
        autoDiv.innerHTML = `
            <div class="auto-nombre">${auto.nombre}</div>
            <div class="auto-datos">P${auto.prioridad} | V${auto.vueltas || 1}</div>
            <div class="auto-orden">${ordenTexto}</div>
        `;
        colaNorteDiv.appendChild(autoDiv);
    });
    // Renderizar autos esperando sur
    const colaSurDiv = document.getElementById('colaSur');
    colaSurDiv.innerHTML = '';
    autosEsperandoSur.forEach((auto, index) => {
        const autoDiv = document.createElement('div');
        autoDiv.className = 'auto-dashboard sur';
        const ordenTexto = index === 0 ? '🟢 PRÓXIMO' : `#${index + 1}`;
        autoDiv.innerHTML = `
            <div class="auto-nombre">${auto.nombre}</div>
            <div class="auto-datos">P${auto.prioridad} | V${auto.vueltas || 1}</div>
            <div class="auto-orden">${ordenTexto}</div>
        `;
        colaSurDiv.appendChild(autoDiv);
    });

    // Estado y total
    document.getElementById('dashboardTotal').textContent = `Total de Autos: ${estado.total_autos}`;
    if (autosEnPuente.length > 0) {
        document.getElementById('dashboardEstado').textContent = `Estado: Ocupado por ${autosEnPuente[0].nombre}`;
    } else {
        document.getElementById('dashboardEstado').textContent = 'Estado: Libre';
    }

    // Si la simulación está iniciada, lanzar solicitudes de cruce para autos en espera
    if (simulacionIniciada) {
        lanzarSimulacionAutos(estado.autos_esperando || []);
    }
}

function actualizarDashboardEstado(texto) {
    document.getElementById('dashboardEstado').textContent = `Estado: ${texto}`;
}

function registrarVehiculoDashboard(event) {
    event.preventDefault();
    const nombre = document.getElementById('vehiculoNombre').value || `Auto_${Math.floor(Math.random() * 9000) + 1000}`;
    const velocidad = parseFloat(document.getElementById('vehiculoVelocidad').value);
    const tiempo_espera = parseFloat(document.getElementById('vehiculoEspera').value);
    const prioridad = parseInt(document.getElementById('vehiculoPrioridad').value);
    const direccion = document.getElementById('vehiculoDireccion').value;
    const vueltas = parseInt(document.getElementById('vehiculoRepeticiones').value) || 1;

    const autoData = {
        nombre: nombre,
        velocidad: velocidad,
        tiempo_espera: tiempo_espera,
        prioridad: prioridad,
        direccion: direccion,
        vueltas: vueltas
    };
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'registrar_auto',
            auto: autoData
        }));
        console.log('Auto registrado desde dashboard:', autoData);
    } else {
        console.error('No hay conexión WebSocket activa');
    }
    
    document.getElementById('formVehiculo').reset();
}

function iniciarSimulacionDashboard() {
    simulacionIniciada = true;
    document.getElementById('btnIniciarSimulacion').disabled = true;
    document.getElementById('btnIniciarSimulacion').textContent = 'Simulación en curso...';
    // Lanzar solicitudes de cruce para los autos en espera actuales
    lanzarSimulacionAutos([...autosEsperandoNorte, ...autosEsperandoSur]);
}

function lanzarSimulacionAutos(autos) {
    autos.forEach(auto => {
        if (!autosSimulando.has(auto.id)) {
            autosSimulando.add(auto.id);
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'solicitar_cruce',
                    auto_id: auto.id
                }));
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    conectarWebSocketDashboard();
}); 