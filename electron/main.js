const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const fs = require('fs')
const { spawn } = require('child_process')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#0d0d0d',
    frame: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  if (isDev) {
    win.loadURL('http://localhost:5173')
  } else {
    win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// IPC: open file dialog
ipcMain.handle('dialog:openFile', async (event, filters) => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: filters || [],
  })
  return result
})

// IPC: save file dialog
ipcMain.handle('dialog:saveFile', async (event, filters) => {
  const result = await dialog.showSaveDialog({
    filters: filters || [],
  })
  return result
})

// IPC: read file — returns base64 string
ipcMain.handle('fs:readFile', async (event, filePath) => {
  try {
    const buffer = fs.readFileSync(filePath)
    return buffer.toString('base64')
  } catch (err) {
    console.error('fs:readFile error:', err)
    return null
  }
})

// IPC: write file
ipcMain.handle('fs:writeFile', async (event, filePath, content) => {
  try {
    fs.writeFileSync(filePath, content)
    return true
  } catch (err) {
    console.error('fs:writeFile error:', err)
    return false
  }
})

// IPC: start render — spawns studio_core_runner.py and streams stdout
ipcMain.handle('render:start', async (event, params) => {
  return new Promise((resolve) => {
    const jsonArg = JSON.stringify(params)
    const child = spawn('python', ['studio_core_runner.py', jsonArg], {
      cwd: path.join(__dirname, '..'),
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    child.stdout.on('data', (data) => {
      const lines = data.toString().split('\n')
      for (const line of lines) {
        if (line) {
          event.sender.send('render:log', line)
        }
      }
    })

    child.stderr.on('data', (data) => {
      const lines = data.toString().split('\n')
      for (const line of lines) {
        if (line) {
          event.sender.send('render:log', '[stderr] ' + line)
        }
      }
    })

    child.on('close', (code) => {
      const success = code === 0
      event.sender.send('render:done', success)
      resolve(success)
    })

    child.on('error', (err) => {
      event.sender.send('render:log', 'Error: ' + err.message)
      event.sender.send('render:done', false)
      resolve(false)
    })
  })
})

// IPC: get app path
ipcMain.handle('app:getPath', async () => {
  return __dirname
})
