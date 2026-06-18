// Minimal Electron wrapper that opens the offline Pokemon Quiz game in its own
// desktop window. The game itself is the single self-contained assets/PokemonQuiz.html
// (ROM + emulator + UI all inlined), so no network access is ever needed.
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

// One clean instance: if the game is already open, focus it instead of opening
// a second window (matters for the portable .exe, which people may double-click twice).
if (!app.requestSingleInstanceLock()) { app.quit(); }

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 480,
    minHeight: 432,
    title: 'Pokemon Quiz',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    center: true,
    show: false,                 // reveal only once painted -> no white flash
    autoHideMenuBar: true,
    backgroundColor: '#0b1f2a',  // matches the game's dark background while it loads
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // No menu bar - it's a kids' game, keep it clean and full of screen.
  Menu.setApplicationMenu(null);

  win.loadFile(path.join(__dirname, 'assets', 'PokemonQuiz.html'));

  // Show the window only once the page has painted, so the first thing the child
  // sees is the game -- never a blank white rectangle.
  win.once('ready-to-show', () => win.show());

  // Open any external links in the real browser rather than inside the app.
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Bring the existing window to the front if a second copy is launched.
app.on('second-instance', () => {
  const win = BrowserWindow.getAllWindows()[0];
  if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
