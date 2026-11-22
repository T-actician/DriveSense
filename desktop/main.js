const { app, BrowserWindow, dialog } = require('electron');
const { autoUpdater } = require('electron-updater');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const PORT = 8765;
const URL = `http://127.0.0.1:${PORT}/`;
const ROOT = path.join(__dirname, '..');
const SPLASH = 'data:text/html;charset=utf-8,' + encodeURIComponent(
  '<body style="margin:0;background:#020a12;color:#1fb6ff;font:700 20px Bahnschrift,Segoe UI,sans-serif;' +
  'letter-spacing:.3em;display:flex;align-items:center;justify-content:center;height:100vh">' +
  'DRIVESENSE // STARTING...</body>');
let py, win, quitting = false;

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

function fail(msg) {
  if (quitting) return;
  quitting = true;
  dialog.showErrorBox('DriveSense', msg);
  app.quit();
}

function readCam() {
  try {
    const s = JSON.parse(fs.readFileSync(path.join(app.getPath('userData'), 'settings.json'), 'utf8'));
    return String(Number.isInteger(s.cam) ? s.cam : 0);
  } catch (e) {
    return '0';
  }
}

function startBackend() {
  const args = ['--cam', readCam(), '--port', String(PORT)];
  const env = { ...process.env, DRIVESENSE_DATA: app.getPath('userData') };
  if (app.isPackaged) {
    py = spawn(path.join(process.resourcesPath, 'backend', 'drivesense-server.exe'), args,
      { cwd: app.getPath('userData'), env, windowsHide: true });
  } else {
    py = spawn(path.join(ROOT, '.venv', 'Scripts', 'python.exe'), ['server.py', ...args],
      { cwd: ROOT, env, windowsHide: true });
  }
  py.stdout.on('data', d => console.log('[py]', d.toString()));
  py.stderr.on('data', d => console.error('[py]', d.toString()));
  py.on('error', e => fail('Could not start the detection engine: ' + e.message));
  py.on('exit', code => fail('The detection engine stopped (code ' + code + ').'));
}

function waitForServer(cb, tries = 0) {
  http.get(URL, r => { r.resume(); cb(); }).on('error', () => {
    if (tries > 200) { fail('The detection engine did not start.'); return; }
    setTimeout(() => waitForServer(cb, tries + 1), 300);
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1366, height: 800, backgroundColor: '#020a12',
    autoHideMenuBar: true, title: 'DriveSense'
  });
  win.loadURL(SPLASH);
  win.webContents.on('before-input-event', (e, i) => {
    if (i.type === 'keyDown' && i.key === 'F11') win.setFullScreen(!win.isFullScreen());
  });
}

function setupUpdates() {
  if (!app.isPackaged) return;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.on('error', e => console.error('[update]', e && e.message));
  autoUpdater.on('update-downloaded', info => {
    dialog.showMessageBox(win, {
      type: 'info',
      buttons: ['Restart now', 'Later'],
      defaultId: 1,
      cancelId: 1,
      title: 'DriveSense update',
      message: 'DriveSense ' + info.version + ' is ready to install.',
      detail: 'Restart now to apply it, or it will install the next time you close DriveSense.'
    }).then(r => {
      if (r.response === 0) {
        quitting = true;
        autoUpdater.quitAndInstall(true, true);
      }
    });
  });
  const check = () => autoUpdater.checkForUpdates().catch(() => {});
  setTimeout(check, 15000);
  setInterval(check, 4 * 60 * 60 * 1000);
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
  });
  app.whenReady().then(() => {
    startBackend();
    createWindow();
    waitForServer(() => win.loadURL(URL));
    setupUpdates();
  });
  app.on('before-quit', () => { quitting = true; if (py) py.kill(); });
  app.on('window-all-closed', () => app.quit());
}