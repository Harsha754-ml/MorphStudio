const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  openFile: (filters) => ipcRenderer.invoke('dialog:openFile', filters),
  saveFile: (filters) => ipcRenderer.invoke('dialog:saveFile', filters),
  readFile: (filePath) => ipcRenderer.invoke('fs:readFile', filePath),
  writeFile: (filePath, content) => ipcRenderer.invoke('fs:writeFile', filePath, content),
  startRender: (params) => ipcRenderer.invoke('render:start', params),
  onRenderLog: (cb) => ipcRenderer.on('render:log', (_, line) => cb(line)),
  onRenderDone: (cb) => ipcRenderer.once('render:done', (_, success) => cb(success)),
  removeRenderListeners: () => {
    ipcRenderer.removeAllListeners('render:log')
    ipcRenderer.removeAllListeners('render:done')
  },
  getAppPath: () => ipcRenderer.invoke('app:getPath'),
})
