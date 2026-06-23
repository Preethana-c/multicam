const express = require('express');
const http = require('http');
const socketio = require('socket.io');
const mqtt = require('mqtt');

const app = express();
const server = http.createServer(app);
const io = socketio(server);

app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

const mqttClient = mqtt.connect('mqtt://localhost:1883');

mqttClient.on('connect', () => {
  console.log('Connected to Mosquitto');
  mqttClient.subscribe('lights/#');
});

mqttClient.on('message', (topic, payload) => {
  const parts = topic.split('/');
  const row = parseInt(parts[1]);
  const col = parseInt(parts[2]);
  const state = payload.toString() === 'ON';
  console.log(`Light (${row},${col}) → ${state ? 'ON' : 'OFF'}`);
  io.emit('light_update', { row, col, state });
});

server.listen(3000, () => {
  console.log('Open http://localhost:3000');
});