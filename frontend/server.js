import http from 'node:http';
import { handler } from './build/handler.js';
import httpProxy from 'http-proxy';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const PORT = process.env.PORT || 3000;

const proxy = httpProxy.createProxyServer({
	target: BACKEND_URL,
	ws: true,
	changeOrigin: true,
});

proxy.on('error', (err, _req, res) => {
	console.error('[proxy] error:', err.message);
	// ⚠️ res est un ServerResponse pour les requêtes HTTP classiques, mais un
	// simple socket pour les upgrades WebSocket (/ws). Appeler writeHead sur un
	// socket lève TypeError et TUE le processus — c'est ce qui figeait l'écran
	// quand le backend n'était pas encore prêt au démarrage (incident des
	// reboots nocturnes de juillet 2026).
	if (res && typeof res.writeHead === 'function') {
		if (!res.headersSent) {
			res.writeHead(502, { 'Content-Type': 'application/json' });
			res.end(JSON.stringify({ detail: 'Backend injoignable' }));
		}
	} else if (res && typeof res.end === 'function') {
		// Upgrade WebSocket : impossible de répondre du HTTP — on ferme le
		// socket proprement ; le navigateur réessaiera (reconnexion auto 3 s).
		try { res.end(); } catch { /* socket déjà mort */ }
	}
});

const server = http.createServer((req, res) => {
	const url = req.url || '';
	// Proxy des requêtes API, médias et WebSocket vers le backend
	if (url.startsWith('/api/') || url.startsWith('/media/')) {
		proxy.web(req, res);
	} else {
		// Tout le reste → SvelteKit
		handler(req, res);
	}
});

// Proxy des connexions WebSocket (/ws) vers le backend
server.on('upgrade', (req, socket, head) => {
	if ((req.url || '').startsWith('/ws')) {
		proxy.ws(req, socket, head);
	}
});

server.listen(PORT, () => {
	console.log(`Snoozolène frontend + proxy listening on port ${PORT} (backend: ${BACKEND_URL})`);
});