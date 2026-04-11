#!/usr/bin/env node
/**
 * Memory V3 HTTP Server
 * Wraps memory.js search as HTTP POST endpoint for harness integration.
 * Port: 3457
 */
const http = require('http');
const { execSync } = require('child_process');
const path = require('path');

const MEMORY_JS = path.join(__dirname, 'memory.js');
const PORT = 3457;

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/search') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const { query, category } = JSON.parse(body);
        if (!query) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'query required' }));
          return;
        }
        const cmd = category
          ? `node "${MEMORY_JS}" search "${query.replace(/"/g, '\\"')}" "${category}"`
          : `node "${MEMORY_JS}" search "${query.replace(/"/g, '\\"')}"`;
        const result = execSync(cmd, { timeout: 15000, encoding: 'utf-8', cwd: path.join(__dirname, '..') });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(result);
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message?.slice(0, 200) || 'search failed' }));
      }
    });
  } else if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Memory V3 server listening on http://127.0.0.1:${PORT}`);
});
