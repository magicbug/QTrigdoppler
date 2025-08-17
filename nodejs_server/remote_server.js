const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const ini = require('ini');

// Try to read config
let port = 5001;
let debug = false;
try {
    const config = ini.parse(fs.readFileSync('./config.ini', 'utf-8'));
    port = config.remote_server?.port || 5001;
    debug = config.remote_server?.debug === 'true';
} catch (error) {
    console.log('Error reading config.ini, using default values');
}

// Create server
const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    },
    pingTimeout: 60000,
    pingInterval: 25000
});

// Store for application state
const appState = {
    tracking: false,
    satellite: null,
    transponder: null,
    rx_offset: 0,
    subtone: 'None',
    satellite_info: {},
    satellite_position: {},
    doppler: {},
    rotator_enabled: false,
    rotator: {}
};

// Track satellite and transponder data
let satelliteList = [];
const transponderLists = {};

// Track client connections
let qtrigClientId = null;
const connectedClients = new Set();
let lastHeartbeat = Date.now();
const serverStartTime = Date.now();

// Serve web client
app.get('/', (req, res) => {
    const webClientPath = path.join(__dirname, 'lib', 'web_api_client.html');
    if (fs.existsSync(webClientPath)) {
        res.sendFile(webClientPath);
    } else {
        res.send("Web client not found. Please ensure web_api_client.html is in the lib directory.");
    }
});

// Health check endpoint
app.get('/status', (req, res) => {
    res.json({
        status: 'running',
        uptime: (Date.now() - serverStartTime) / 1000,
        qtrig_connected: (Date.now() - lastHeartbeat) < 30000,
        clients: connectedClients.size
    });
});

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id} (Total: ${connectedClients.size + 1})`);
    connectedClients.add(socket.id);
    
    // Send current state to new client
    socket.emit('status', appState);
    
    // Send satellite list if available
    if (satelliteList.length > 0) {
        socket.emit('satellite_list', {
            satellites: satelliteList,
            current: appState.satellite
        });
    }
    
    // Send transponder list if satellite is selected
    if (appState.satellite && transponderLists[appState.satellite]) {
        socket.emit('transponder_list', {
            transponders: transponderLists[appState.satellite],
            current: appState.transponder
        });
    }
    
    // Register QTrigdoppler client
    socket.on('register_qtrig_client', () => {
        qtrigClientId = socket.id;
        console.log(`QTrigdoppler client registered with ID: ${socket.id}`);
        socket.emit('registration_success', { status: 'success' });
    });
    
    // Handle heartbeat from QTrigdoppler client
    socket.on('heartbeat', (data) => {
        lastHeartbeat = Date.now();
        if (data.state) {
            updateState(data.state);
        }
    });
    
    // Handle commands from web clients to QTrigdoppler
    socket.on('start_tracking', () => {
        if (qtrigClientId) {
            io.to(qtrigClientId).emit('cmd_start_tracking');
        }
    });
    
    socket.on('stop_tracking', () => {
        if (qtrigClientId) {
            io.to(qtrigClientId).emit('cmd_stop_tracking');
        }
    });
    
    socket.on('select_satellite', (data) => {
        if (qtrigClientId && data.satellite) {
            io.to(qtrigClientId).emit('cmd_select_satellite', data);
        }
    });
    
    socket.on('select_transponder', (data) => {
        if (qtrigClientId && data.transponder) {
            io.to(qtrigClientId).emit('cmd_select_transponder', data);
        }
    });
    
    socket.on('set_subtone', (data) => {
        if (qtrigClientId && data.subtone !== undefined) {
            io.to(qtrigClientId).emit('cmd_set_subtone', data);
        }
    });
    
    socket.on('set_rx_offset', (data) => {
        if (qtrigClientId && data.offset !== undefined) {
            io.to(qtrigClientId).emit('cmd_set_rx_offset', data);
        }
    });
    
    socket.on('park_rotator', () => {
        if (qtrigClientId) {
            io.to(qtrigClientId).emit('cmd_park_rotator');
        }
    });
    
    socket.on('stop_rotator', () => {
        if (qtrigClientId) {
            io.to(qtrigClientId).emit('cmd_stop_rotator');
        }
    });
    
    // Handle data updates from QTrigdoppler
    socket.on('update_satellite_list', (data) => {
        if (data.satellites) {
            satelliteList = data.satellites;
            io.emit('satellite_list', {
                satellites: satelliteList,
                current: appState.satellite
            });
        }
    });
    
    socket.on('update_transponder_list', (data) => {
        if (data.satellite && data.transponders) {
            transponderLists[data.satellite] = data.transponders;
            io.emit('transponder_list', {
                transponders: data.transponders,
                current: appState.transponder
            });
        }
    });
    
    // Handle requests for lists
    socket.on('get_satellite_list', () => {
        socket.emit('satellite_list', {
            satellites: satelliteList,
            current: appState.satellite
        });
    });
    
    socket.on('get_transponder_list', (data) => {
        if (data.satellite && transponderLists[data.satellite]) {
            socket.emit('transponder_list', {
                transponders: transponderLists[data.satellite],
                current: appState.transponder
            });
        } else if (qtrigClientId && data.satellite) {
            io.to(qtrigClientId).emit('cmd_get_transponder_list', data);
        }
    });
    
    // Handle disconnection
    socket.on('disconnect', () => {
        connectedClients.delete(socket.id);
        if (socket.id === qtrigClientId) {
            qtrigClientId = null;
            console.log("QTrigdoppler client disconnected!");
        }
        console.log(`Client disconnected: ${socket.id} (Total: ${connectedClients.size})`);
    });
});

// Update application state and broadcast to all clients
function updateState(stateUpdate) {
    Object.assign(appState, stateUpdate);
    io.emit('status', appState);
}

// Start the server
server.listen(port, '0.0.0.0', () => {
    console.log(`QTrigdoppler Remote Server running on port ${port}`);
    console.log(`Access the web interface at: http://your-server-address:${port}/`);
    console.log(`Configure QTrigdoppler with this URL in your config.ini`);
});
