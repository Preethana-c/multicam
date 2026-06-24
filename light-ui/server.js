const express = require('express');
const http = require('http');
const socketio = require('socket.io');
const mqtt = require('mqtt');

const app = express();
const server = http.createServer(app);
const io = socketio(server);

app.use(express.json());

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

let floorClicks = [];

app.post('/click', (req, res) => {
  const { tile_col, tile_row, label, cam } = req.body;
  floorClicks.push({ tile_col, tile_row, label, cam });
  console.log(`floor click: cam=${cam} label=${label} tile=(${tile_col},${tile_row})`);
  res.json({ ok: true });
});

app.get('/clicks', (req, res) => {
  res.json(floorClicks);
});

app.delete('/clicks', (req, res) => {
  floorClicks = [];
  res.json({ ok: true });
});

server.listen(3000, () => {
  console.log('Open http://localhost:3000');
});