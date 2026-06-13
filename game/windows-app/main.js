// Minimal Electron wrapper that opens the offline Pokemon Quiz game in its own
// desktop window. The game itself is the single self-contained assets/PokemonQuiz.html
// (ROM + emulator + UI all inlined), so no network access is ever needed.
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1024,
    height: 768,
    minWidth: 480,
    minHeight: 432,
    title: 'Pokemon Quiz',
    autoHideMenuBar: true,
    backgroundColor: '#000000',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // No menu bar - it's a kids' game, keep it clean and full of screen.
  Menu.setApplicationMenu(null);

  win.loadFile(path.join(__dirname, 'assets', 'PokemonQuiz.html'));

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

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
