// content.js - This runs on EVERY website automatically!

class A11yOverlay {
    constructor() {
        this.config = {
            backendUrl: 'http://localhost:8000', // Your friend's backend
            wakeWord: 'hey assistant'
        };
        
        this.state = {
            isActive: false,
            sessionId: null,
            currentPage: null,
            actions: []
        };
        
        this.init();
    }
    
    init() {
        // Create container
        this.container = document.createElement('div');
        this.container.id = 'a11y-overlay-root';
        document.body.appendChild(this.container);
        
        // DON'T inject styles here - they come from widget.css
        
        // Add trigger button
        this.addTriggerButton();
        
        // Initialize voice if available
        if ('webkitSpeechRecognition' in window) {
            this.initVoiceRecognition();
        }
        
        console.log('A11y Overlay loaded on:', window.location.href);
        
        // Listen for messages from popup/background
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === 'analyzePage') {
                this.analyzeCurrentPage();
            }
            if (request.action === 'toggleVoice') {
                this.toggleVoiceListening();
            }
            if (request.action === 'toggleWidget') {
                this.togglePanel();
            }
        });
    }
    
    addTriggerButton() {
        this.triggerBtn = document.createElement('button');
        this.triggerBtn.className = 'a11y-trigger-btn';
        this.triggerBtn.innerHTML = '🎤';
        this.triggerBtn.title = 'A11y Assistant';
        
        this.triggerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.togglePanel();
        });
        
        this.container.appendChild(this.triggerBtn);
        
        // Add panel
        this.panel = document.createElement('div');
        this.panel.className = 'a11y-control-panel';
        this.panel.innerHTML = `
            <div class="a11y-panel-header">
                <h3 class="a11y-panel-title">A11y Assistant</h3>
                <p class="a11y-panel-subtitle">AI navigation helper</p>
            </div>
            <div class="a11y-panel-content">
                <div style="margin-bottom: 16px; font-size: 14px; color: #6b7280;">
                    Say "hey assistant" or click below
                </div>
                <div id="a11y-actions">
                    <button class="a11y-action-btn primary" id="analyze-btn">
                        🔍 Analyze This Page
                    </button>
                </div>
            </div>
        `;
        
        this.container.appendChild(this.panel);
        
        // Add event listeners
        this.panel.querySelector('#analyze-btn').addEventListener('click', () => {
            this.analyzeCurrentPage();
        });
    }
    
    togglePanel() {
        if (this.panel.classList.contains('active')) {
            this.panel.classList.remove('active');
        } else {
            this.panel.classList.add('active');
            if (!this.state.currentPage) {
                this.analyzeCurrentPage();
            }
        }
    }
    
    async analyzeCurrentPage() {
        try {
            // Show loading
            const analyzeBtn = this.panel.querySelector('#analyze-btn');
            const originalText = analyzeBtn.innerHTML;
            analyzeBtn.innerHTML = '⏳ Analyzing...';
            analyzeBtn.disabled = true;
            
            // Load html2canvas dynamically
            await this.loadHtml2Canvas();
            
            // Capture screenshot
            const screenshot = await this.captureScreenshot();
            
            // Capture DOM elements
            const domElements = this.captureDomElements();
            
            // Send to backend
            const response = await this.sendToBackend('/api/analyze-page', {
                screenshot: screenshot,
                dom_elements: JSON.stringify(domElements),
                url: window.location.href
            });
            
            this.state.sessionId = response.session_id;
            this.state.currentPage = response.analysis;
            this.state.actions = response.analysis.actions || [];
            
            // Display actions
            this.displayActions(this.state.actions);
            
            // Reset button
            analyzeBtn.innerHTML = originalText;
            analyzeBtn.disabled = false;
            
        } catch (error) {
            console.error('Analysis failed:', error);
            const analyzeBtn = this.panel.querySelector('#analyze-btn');
            analyzeBtn.innerHTML = '❌ Failed - Try Again';
            analyzeBtn.disabled = false;
            
            // Show error message
            const actionsContainer = this.panel.querySelector('#a11y-actions');
            actionsContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #dc2626;">
                    <p>Failed to analyze page.</p>
                    <p>Make sure backend is running at ${this.config.backendUrl}</p>
                </div>
            `;
        }
    }
    
    loadHtml2Canvas() {
        return new Promise((resolve, reject) => {
            if (typeof html2canvas !== 'undefined') {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    captureScreenshot() {
        return new Promise((resolve, reject) => {
            html2canvas(document.documentElement, {
                scale: 0.5,
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff'
            }).then(canvas => {
                const screenshot = canvas.toDataURL('image/jpeg', 0.7);
                resolve(screenshot);
            }).catch(reject);
        });
    }
    
    captureDomElements() {
        const selectors = [
            'button:not([disabled])',
            'a[href]:not([href="#"])',
            'input:not([type="hidden"]):not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[role="button"]',
            '[role="link"]',
            '[tabindex]:not([tabindex="-1"])'
        ].join(', ');
        
        const allElements = document.querySelectorAll(selectors);
        const elements = [];
        
        allElements.forEach((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            
            const isVisible = (
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                style.opacity !== '0' &&
                rect.width > 0 &&
                rect.height > 0 &&
                rect.top < window.innerHeight &&
                rect.bottom > 0
            );
            
            if (!isVisible) return;
            
            // Get element text/label
            let text = '';
            if (el.textContent && el.textContent.trim()) {
                text = el.textContent.trim().substring(0, 100);
            } else if (el.getAttribute('aria-label')) {
                text = el.getAttribute('aria-label');
            } else if (el.getAttribute('placeholder')) {
                text = el.getAttribute('placeholder');
            } else if (el.value) {
                text = el.value;
            } else if (el.alt) {
                text = el.alt;
            } else if (el.title) {
                text = el.title;
            }
            
            elements.push({
                index: index,
                tag: el.tagName.toLowerCase(),
                text: text,
                type: el.type || '',
                id: el.id,
                classes: Array.from(el.classList),
                selector: this.generateSelector(el),
                bounds: {
                    x: rect.x + window.scrollX,
                    y: rect.y + window.scrollY,
                    width: rect.width,
                    height: rect.height
                }
            });
        });
        
        return elements.slice(0, 50);
    }
    
    generateSelector(element) {
        if (element.id) {
            return '#' + element.id;
        }
        
        if (element.getAttribute('data-testid')) {
            return `[data-testid="${element.getAttribute('data-testid')}"]`;
        }
        
        if (element.classList.length > 0) {
            return '.' + Array.from(element.classList).join('.');
        }
        
        return element.tagName.toLowerCase();
    }
    
    displayActions(actions) {
        const actionsContainer = this.panel.querySelector('#a11y-actions');
        actionsContainer.innerHTML = '';
        
        if (!actions || actions.length === 0) {
            actionsContainer.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #6b7280;">
                    <p>No actions found.</p>
                </div>
            `;
            return;
        }
        
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'a11y-action-btn';
            if (action.confidence > 0.7) {
                button.classList.add('primary');
            }
            
            button.innerHTML = `
                <strong>${action.label || 'Action'}</strong>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">
                    ${action.description || ''}
                </div>
            `;
            
            button.addEventListener('click', () => {
                this.executeAction(action);
            });
            
            actionsContainer.appendChild(button);
        });
    }
    
    async executeAction(action) {
        try {
            // Highlight the element
            if (action.element_index !== undefined) {
                this.highlightElement(action.element_index);
            }
            
            // Simulate click on the element
            const elements = this.captureDomElements();
            if (action.element_index < elements.length) {
                const element = document.querySelector(elements[action.element_index].selector);
                if (element) {
                    element.click();
                    this.showNotification(`Clicked: ${action.label}`);
                }
            }
            
            // Close panel after action
            setTimeout(() => {
                this.panel.classList.remove('active');
            }, 1000);
            
        } catch (error) {
            console.error('Action execution failed:', error);
            this.showNotification('Failed to execute action');
        }
    }
    
    highlightElement(elementIndex) {
        // Remove existing highlights
        document.querySelectorAll('.a11y-highlight-box').forEach(el => el.remove());
        
        const elements = this.captureDomElements();
        if (elementIndex < elements.length) {
            const element = document.querySelector(elements[elementIndex].selector);
            if (element) {
                const rect = element.getBoundingClientRect();
                
                const highlight = document.createElement('div');
                highlight.className = 'a11y-highlight-box';
                highlight.style.cssText = `
                    left: ${rect.left + window.scrollX}px;
                    top: ${rect.top + window.scrollY}px;
                    width: ${rect.width}px;
                    height: ${rect.height}px;
                `;
                
                document.body.appendChild(highlight);
                
                setTimeout(() => highlight.remove(), 3000);
            }
        }
    }
    
    showNotification(message) {
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #1f2937;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 2147483647;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    initVoiceRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;
        
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onstart = () => {
            this.triggerBtn.classList.add('listening');
        };
        
        this.recognition.onend = () => {
            this.triggerBtn.classList.remove('listening');
        };
        
        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                }
            }
            
            if (finalTranscript.toLowerCase().includes(this.config.wakeWord)) {
                this.togglePanel();
            }
        };
    }
    
    toggleVoiceListening() {
        if (!this.recognition) return;
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('Voice recognition error:', error);
        }
    }
    
    async sendToBackend(endpoint, data) {
        const formData = new FormData();
        Object.keys(data).forEach(key => {
            formData.append(key, data[key]);
        });
        
        const response = await fetch(this.config.backendUrl + endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }
        
        return await response.json();
    }
}

// Auto-initialize on every page
window.addEventListener('load', () => {
    setTimeout(() => {
        window.a11yOverlay = new A11yOverlay();
    }, 1000);
});