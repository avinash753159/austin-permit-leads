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

  // ─── API: View collected emails (password protected, browser-friendly) ───
  if (req.url.startsWith('/api/leads') && req.method === 'GET') {
    const url = new URL(req.url, 'http://localhost');
    const pw = url.searchParams.get('pw');
    const ADMIN_PW = process.env.ADMIN_PASSWORD || 'Roopa1134!';

    if (pw !== ADMIN_PW) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(`<!DOCTYPE html><html><head><title>Brimstone Admin</title>
        <style>body{font-family:system-ui;background:#FDFBF7;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
        .box{background:white;padding:36px;border-radius:16px;box-shadow:0 8px 24px rgba(44,24,16,0.08);text-align:center;max-width:360px;width:90%;}
        h2{font-size:20px;color:#2C1810;margin-bottom:16px;}
        input{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px;margin-bottom:12px;box-sizing:border-box;}
        button{width:100%;padding:12px;background:#2C1810;color:#FDFBF7;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;}
        </style></head><body><div class="box"><h2>Brimstone Admin</h2>
        <form method="GET"><input type="password" name="pw" placeholder="Password" autofocus>
        <button type="submit">View Leads</button></form></div></body></html>`);
      return;
    }

    const leads = JSON.parse(fs.readFileSync(LEADS_FILE, 'utf8'));
    res.writeHead(200, { 'Content-Type': 'text/html' });
    let rows = leads.map(l => `<tr><td>${l.email}</td><td>${l.source||''}</td><td>${l.city||''}</td><td>${l.date||''}</td></tr>`).join('');
    if (!rows) rows = '<tr><td colspan="4" style="text-align:center;color:#aaa;padding:40px;">No emails collected yet</td></tr>';
    res.end(`<!DOCTYPE html><html><head><title>Brimstone Leads</title>
      <style>body{font-family:system-ui;background:#FDFBF7;padding:40px;margin:0;color:#2C1810;}
      h1{font-size:24px;margin-bottom:4px;}p{color:#8C7E73;margin-bottom:24px;}
      table{width:100%;max-width:800px;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(44,24,16,0.06);}
      th{background:#2C1810;color:#FDFBF7;padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;}
      td{padding:12px 16px;border-bottom:1px solid #f0ece6;font-size:14px;}
      tr:last-child td{border:none;}
      .count{background:#C4763A;color:white;padding:4px 12px;border-radius:100px;font-size:13px;font-weight:600;}
      </style></head><body>
      <h1>Collected Leads <span class="count">${leads.length}</span></h1>
      <p>Emails from CSV exports and weekly subscriptions</p>
      <table><thead><tr><th>Email</th><th>Source</th><th>City</th><th>Date</th></tr></thead>
      <tbody>${rows}</tbody></table></body></html>`);
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
