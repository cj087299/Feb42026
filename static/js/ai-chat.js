/* AI Chat Widget JavaScript */

class AIChatWidget {
    constructor() {
        this.isOpen = false;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        this.createWidget();
        this.attachEventListeners();
        this.showWelcomeMessage();
    }

    createWidget() {
        const widget = document.createElement('div');
        widget.className = 'ai-chat-widget';
        widget.innerHTML = `
            <button class="ai-chat-toggle" id="aiChatToggle">
                🤖
                <span class="ai-chat-badge" id="aiChatBadge">!</span>
            </button>
            <div class="ai-chat-container" id="aiChatContainer">
                <div class="ai-chat-header">
                    <h3>💬 AI Assistant</h3>
                    <button class="ai-chat-close" id="aiChatClose">×</button>
                </div>
                <div class="ai-chat-messages" id="aiChatMessages">
                    <!-- Messages will be added here -->
                </div>
                <div class="ai-chat-input-container">
                    <div class="ai-chat-input-wrapper">
                        <input 
                            type="text" 
                            class="ai-chat-input" 
                            id="aiChatInput" 
                            placeholder="Ask me anything about VZT Accounting..."
                            maxlength="500"
                            aria-label="Chat message input (max 500 characters)"
                        />
                        <button class="ai-chat-send" id="aiChatSend">Send</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(widget);
    }

    attachEventListeners() {
        const toggle = document.getElementById('aiChatToggle');
        const close = document.getElementById('aiChatClose');
        const send = document.getElementById('aiChatSend');
        const input = document.getElementById('aiChatInput');

        toggle.addEventListener('click', () => this.toggle());
        close.addEventListener('click', () => this.close());
        send.addEventListener('click', () => this.sendMessage());
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    toggle() {
        this.isOpen = !this.isOpen;
        const container = document.getElementById('aiChatContainer');
        const toggle = document.getElementById('aiChatToggle');
        const badge = document.getElementById('aiChatBadge');
        
        if (this.isOpen) {
            container.classList.add('active');
            toggle.classList.add('active');
            badge.classList.remove('active');
            document.getElementById('aiChatInput').focus();
        } else {
            container.classList.remove('active');
            toggle.classList.remove('active');
        }
    }

    close() {
        this.isOpen = false;
        document.getElementById('aiChatContainer').classList.remove('active');
        document.getElementById('aiChatToggle').classList.remove('active');
    }

    showWelcomeMessage() {
        setTimeout(() => {
            this.addMessage('assistant', 
                'Hello! 👋 I\'m your AI assistant for VZT Accounting. I can help you with:\n\n' +
                '• Understanding features\n' +
                '• Invoice management\n' +
                '• Cash flow projections\n' +
                '• User roles & permissions\n' +
                '• QuickBooks integration\n\n' +
                'What would you like to know?'
            );
            // Show badge to get user's attention
            document.getElementById('aiChatBadge').classList.add('active');
        }, 2000);
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('aiChatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-chat-message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'ai-chat-message-content';
        contentDiv.textContent = content;
        
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Add to conversation history
        this.conversationHistory.push({
            role: role,
            content: content
        });
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('aiChatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'ai-chat-message assistant';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="ai-chat-typing active">
                <div class="ai-chat-typing-dots">
                    <span class="ai-chat-typing-dot"></span>
                    <span class="ai-chat-typing-dot"></span>
                    <span class="ai-chat-typing-dot"></span>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const typingDiv = document.getElementById('typingIndicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    async sendMessage() {
        const input = document.getElementById('aiChatInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message
        this.addMessage('user', message);
        input.value = '';
        
        // Disable send button
        const sendBtn = document.getElementById('aiChatSend');
        sendBtn.disabled = true;
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send to API
            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    history: this.conversationHistory.slice(-10) // Send last 10 messages
                })
            });
            
            this.hideTypingIndicator();
            
            if (!response.ok) {
                throw new Error('Failed to get AI response');
            }
            
            const data = await response.json();
            this.addMessage('assistant', data.response);
            
        } catch (error) {
            console.error('AI Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', 
                'I apologize, but I encountered an error. Please try again or contact support if the issue persists.'
            );
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }
}

// Initialize chat widget when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.aiChat = new AIChatWidget();
    });
} else {
    window.aiChat = new AIChatWidget();
}
