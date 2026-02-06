// popup.js - Fixed with error handling
document.getElementById('analyze-btn').addEventListener('click', async () => {
    const status = document.getElementById('status');
    status.textContent = 'Sending to page...';
    
    try {
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        
        if (!tab) {
            status.textContent = 'No active tab found';
            return;
        }
        
        // Send message to content script
        const response = await chrome.tabs.sendMessage(tab.id, {action: 'analyzePage'});
        status.textContent = 'Analysis started!';
        
    } catch (error) {
        console.error('Error:', error);
        status.textContent = 'Error: Page not ready. Refresh and try again.';
    }
});

document.getElementById('voice-btn').addEventListener('click', async () => {
    const status = document.getElementById('status');
    
    try {
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        
        if (!tab) {
            status.textContent = 'No active tab found';
            return;
        }
        
        await chrome.tabs.sendMessage(tab.id, {action: 'toggleVoice'});
        status.textContent = 'Voice toggled';
        
    } catch (error) {
        console.error('Error:', error);
        status.textContent = 'Voice not available on this page';
    }
});

document.getElementById('help-btn').addEventListener('click', () => {
    chrome.tabs.create({ url: chrome.runtime.getURL('help.html') });
});

// Update popup status on open
document.addEventListener('DOMContentLoaded', () => {
    const status = document.getElementById('status');
    status.textContent = 'Ready - Click buttons above';
});