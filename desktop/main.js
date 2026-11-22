const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

const PORT = 8765;
const ROOT = path.join(__dirname, '..');
let py;

function startBackend() {
  py = spawn(path.join(ROOT, '.venv', 'Scripts', 'python.exe'),
    ['server.py', '--cam', '1', '--port', String(PORT)], { cwd: ROOT, windowsHide: true });
  py.stdout.on('data', d => console.log('[py]', d.toString()));
  py.stderr.on('data', d => console.error('[py]', d.toString()));
}

function waitForServer(cb) {
  const t = setInterval(() => {
    http.get(`http://127.0.0.1:${PORT}/`, r => { clearInterval(t); r.resume(); cb(); })
      .on('error', () => {});
  }, 300);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1366, height: 800, backgroundColor: '#020a12',
    autoHideMenuBar: true, title: 'DriveSense'
  });
  win.loadURL(`http://127.0.0.1:${PORT}/`);
  win.webContents.on('before-input-event', (e, i) => {
    if (i.type === 'keyDown' && i.key === 'F11') win.setFullScreen(!win.isFullScreen());
  });
}

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.whenReady().then(() => { startBackend(); waitForServer(createWindow); });
app.on('before-quit', () => { if (py) py.kill(); });
app.on('window-all-closed', () => app.quit());