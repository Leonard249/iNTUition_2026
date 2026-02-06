// background.js - SUPER SIMPLE version
console.log('A11y Assistant background script started');

// Set default settings on install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed/updated');
    
    chrome.storage.sync.set({
        backendUrl: 'http://localhost:8000',
        enabled: true,
        wakeWord: 'hey assistant'
    });
});

// Just forward messages between popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message:', request.action);
    
    if (request.action === 'analyzePage') {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { action: 'analyzePage' });
                sendResponse({ success: true });
            }
        });
        return true;
    }
    
    if (request.action === 'toggleVoice') {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { action: 'toggleVoice' });
                sendResponse({ success: true });
            }
        });
        return true;
    }
    
    if (request.action === 'getSettings') {
        chrome.storage.sync.get(['backendUrl', 'enabled'], (settings) => {
            sendResponse(settings);
        });
        return true;
    }
});