import http from 'http';
import { searchMemory } from './memory.js';

const PORT = 3457;

const server = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/search') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', async () => {
      try {
        const { query } = JSON.parse(body);
        if (!query) { res.writeHead(400); res.end('query required'); return; }
        const r = await searchMemory(query);
        const items = r?.results || (Array.isArray(r) ? r : []);
        const text = items.slice(0, 5).map(i => `- ${(i.text || '').slice(0, 200)}`).join('\n');
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify(text || 'No matching memories found.'));
      } catch (e) {
        res.writeHead(500, { 'content-type': 'application/json' });
        res.end(JSON.stringify('Memory search error: ' + e.message));
      }
    });
  } else if (req.url === '/health') {
    res.writeHead(200); res.end('ok');
  } else {
    res.writeHead(404); res.end('Not found');
  }
});

server.listen(PORT, '127.0.0.1', () => console.log(`Memory V3 on :${PORT}`));
