const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const LEADS_FILE = path.join(__dirname, 'collected-emails.json');

// Initialize leads file if it doesn't exist
if (!fs.existsSync(LEADS_FILE)) {
  fs.writeFileSync(LEADS_FILE, '[]');
}

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.csv': 'text/csv',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

http.createServer((req, res) => {
  // ─── API: Collect email ───
  if (req.method === 'POST' && req.url === '/api/collect-email') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { email, city } = JSON.parse(body);
        if (!email || !email.includes('@')) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid email' }));
          return;
        }

        const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
        leads.push({
          email,
          city: city || 'unknown',
          date: new Date().toISOString(),
          source: 'csv-export'
        });
        fs.writeFileSync(LEADS_FILE, JSON.stringify(leads, null, 2));

        console.log(`[LEAD] ${email} (${city}) - ${new Date().toISOString()}`);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Bad request' }));
      }
    });
    return;
  }

  // ─── API: Subscribe (weekly report) ───
  if (req.method === 'POST' && req.url === '/api/subscribe') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { email } = JSON.parse(body);
        if (!email || !email.includes('@')) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid email' }));
          return;
        }

        const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
        leads.push({
          email,
          date: new Date().toISOString(),
          source: 'weekly-subscribe'
        });
        fs.writeFileSync(LEADS_FILE, JSON.stringify(leads, null, 2));

        console.log(`[SUBSCRIBE] ${email} - ${new Date().toISOString()}`);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Bad request' }));
      }
    });
    return;
  }

  // ─── API: View collected emails (protected) ───
  if (req.url === '/api/leads' && req.method === 'GET') {
    const auth = req.headers['x-api-key'];
    if (auth !== (process.env.API_KEY || 'brimstone2026')) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unauthorized' }));
      return;
    }
    const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(leads));
    return;
  }

  // ─── Static files ───
  let filePath = req.url.split('?')[0];
  if (filePath === '/') filePath = '/index.html';

  const fullPath = path.join(__dirname, filePath);
  const ext = path.extname(fullPath);

  fs.readFile(fullPath, (err, data) => {
    if (err) {
      fs.readFile(path.join(__dirname, 'index.html'), (err2, data2) => {
        if (err2) {
          res.writeHead(404);
          res.end('Not found');
        } else {
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(data2);
        }
      });
    } else {
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      res.end(data);
    }
  });
}).listen(PORT, () => console.log(`Brimstone running on port ${PORT}`));
