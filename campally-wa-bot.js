const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, downloadMediaMessage } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const axios   = require('axios');
const express = require('express');
const QRCode  = require('qrcode');
const pino    = require('pino');

const DJANGO = 'http://localhost/whatsapp/baileys/';
const SOCKET = '/home/ubterfinder864tt/CampyAlly/campally.sock';
const PORT   = 3001;

let currentQR   = null;
let isConnected = false;

const app = express();
app.get('/', async (req, res) => {
  if (isConnected) {
    return res.send('<html><body style="background:#111;color:#25D366;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0"><h1>Connected!</h1></body></html>');
  }
  if (!currentQR) {
    return res.send('<html><body style="background:#111;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0"><div style="text-align:center"><h2>Generating QR...</h2><script>setTimeout(()=>location.reload(),5000)</script></div></body></html>');
  }
  const qrImg = await QRCode.toDataURL(currentQR, { width: 320 });
  res.send(`<html><head><title>CampAlly QR</title></head><body style="background:#111;display:flex;justify-content:center;align-items:center;flex-direction:column;height:100vh;margin:0;font-family:sans-serif;color:#fff">
    <h2 style="color:#25D366">Scan with WhatsApp</h2>
    <p style="color:#aaa">Open WhatsApp > Linked Devices > Link a Device</p>
    <img src="${qrImg}" style="border-radius:12px">
    <script>setTimeout(()=>location.reload(),30000)</script>
  </body></html>`);
});
app.listen(PORT, () => console.log('[QR] Server on port ' + PORT));

async function handleMessage(sock, msg) {
  const from = msg.key.remoteJid;
  if (from.endsWith('@g.us')) return;
  const phone = from.replace('@s.whatsapp.net', '');

  const msgObj  = msg.message || {};
  const msgType = Object.keys(msgObj)[0] || '';

  const isText     = msgType === 'conversation' || msgType === 'extendedTextMessage';
  const isVoice    = msgType === 'pttMessage' || msgType === 'audioMessage';
  const isImage    = msgType === 'imageMessage';
  const isLocation = msgType === 'locationMessage' || msgType === 'liveLocationMessage';

  try {
    // ── Text ────────────────────────────────────────────────────
    if (isText) {
      const text = (msgObj.conversation || msgObj.extendedTextMessage?.text || '').trim();
      if (!text) return;
      console.log('[WA] <- text ' + phone + ': ' + text.slice(0, 60));
      const { data } = await axios.post(DJANGO, { phone, body: text, type: 'text' },
        { socketPath: SOCKET, timeout: 45000 });
      if (data.reply) await sock.sendMessage(from, { text: data.reply });

    // ── Voice note ───────────────────────────────────────────────
    } else if (isVoice) {
      console.log('[WA] <- voice ' + phone);
      const buffer   = await downloadMediaMessage(msg, 'buffer', {});
      const audioB64 = buffer.toString('base64');
      const mimeType = msgObj[msgType]?.mimetype || 'audio/ogg; codecs=opus';
      const { data } = await axios.post(DJANGO,
        { phone, type: 'audio', audio_b64: audioB64, mime_type: mimeType, body: '' },
        { socketPath: SOCKET, timeout: 90000 });
      if (data.reply) await sock.sendMessage(from, { text: data.reply });

    // ── Image ────────────────────────────────────────────────────
    } else if (isImage) {
      console.log('[WA] <- image ' + phone);
      const buffer   = await downloadMediaMessage(msg, 'buffer', {});
      const imageB64 = buffer.toString('base64');
      const mimeType = msgObj.imageMessage?.mimetype || 'image/jpeg';
      const caption  = msgObj.imageMessage?.caption || '';
      const { data } = await axios.post(DJANGO,
        { phone, type: 'image', image_b64: imageB64, mime_type: mimeType, body: caption },
        { socketPath: SOCKET, timeout: 60000 });
      if (data.reply) await sock.sendMessage(from, { text: data.reply });

    // ── Location share ───────────────────────────────────────────
    } else if (isLocation) {
      const locObj  = msgObj.locationMessage || msgObj.liveLocationMessage || {};
      const lat     = locObj.degreesLatitude;
      const lng     = locObj.degreesLongitude;
      const name    = locObj.name    || '';
      const address = locObj.address || '';
      if (lat == null || lng == null) return;
      console.log('[WA] <- location ' + phone + ': lat=' + lat + ', lng=' + lng + (name ? ' (' + name + ')' : ''));
      const { data } = await axios.post(DJANGO,
        { phone, type: 'location', latitude: lat, longitude: lng, name, address, body: '' },
        { socketPath: SOCKET, timeout: 45000 });
      if (data.reply) await sock.sendMessage(from, { text: data.reply });
    }
  } catch (err) {
    console.error('[WA] Error:', err.message);
    try {
      await sock.sendMessage(from, { text: 'Sorry, something went wrong. Please try again.' });
    } catch (_) {}
  }
}

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
  const { version } = await fetchLatestBaileysVersion();
  const sock = makeWASocket({
    version, auth: state, printQRInTerminal: true,
    logger: pino({ level: 'silent' }),
  });

  sock.ev.on('creds.update', saveCreds);

  // ── Reject incoming calls & send a text reply ────────────────
  sock.ev.on('call', async (calls) => {
    for (const call of calls) {
      if (call.status === 'offer') {
        console.log('[WA] Incoming call from ' + call.from + ' — rejecting');
        try {
          await sock.rejectCall(call.id, call.from);
        } catch (e) {
          console.log('[WA] Could not reject call:', e.message);
        }
        // Send a friendly auto-reply text after rejecting
        try {
          await sock.sendMessage(call.from, {
            text:
              '📵 Hi! I\'m *CampAlly*, an automated WhatsApp bot — I can\'t take calls.\n\n' +
              'Please *type your message* and I\'ll help you with:\n' +
              '1. 🅿️ Parking at Redemption City\n' +
              '2. 📍 Find places nearby\n' +
              '3. 🆘 Report an emergency\n' +
              '4. 🔍 Lost & Found\n\n' +
              'How can I help you? 😊'
          });
        } catch (e) {
          console.log('[WA] Could not send post-call reply:', e.message);
        }
      }
    }
  });

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) { currentQR = qr; isConnected = false; }
    if (connection === 'close') {
      isConnected = false; currentQR = null;
      const code = lastDisconnect?.error?.output?.statusCode;
      if (code !== DisconnectReason.loggedOut) {
        console.log('[WA] Reconnecting...');
        setTimeout(connectToWhatsApp, 3000);
      } else {
        console.log('[WA] Logged out');
      }
    } else if (connection === 'open') {
      isConnected = true; currentQR = null;
      sock.updateProfileName('CampAlly').catch(e => console.log('[WA] Name update:', e.message));
      console.log('[WA] Connected!');
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    const msg = messages[0];
    if (!msg.message || msg.key.fromMe) return;
    await handleMessage(sock, msg);
  });
}

connectToWhatsApp();
