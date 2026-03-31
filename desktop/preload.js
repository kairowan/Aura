const { contextBridge, ipcRenderer } = require('electron');

const SELECT_PROJECT_DIRECTORY_CHANNEL = 'aura:select-project-directory';

contextBridge.exposeInMainWorld('auraDesktop', {
  selectProjectDirectory: () =>
    ipcRenderer.invoke(SELECT_PROJECT_DIRECTORY_CHANNEL),
});
