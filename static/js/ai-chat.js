/* AI Chat Widget JavaScript */

class AIChatWidget {
    constructor() {
        this.isOpen = false;
        this.conversationHistory = [];
        this.advancedMode = false;
        this.userRole = null;
        this.init();
    }

    init() {
        this.createWidget();
        this.attachEventListeners();
        this.checkUserRole();
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
                    <div id="advancedModeIndicator" style="display: none; padding: 8px; background: #fef3c7; border-radius: 4px; margin-bottom: 8px; font-size: 12px;">
                        <strong>⚡ Advanced Mode Active</strong> - AI can perform actions and code modifications
                    </div>
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
                    <div id="advancedModeToggle" style="display: none; margin-top: 8px; text-align: center;">
                        <button id="toggleAdvancedMode" style="padding: 6px 12px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
                            🔓 Enable Advanced Mode
                        </button>
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
        
        // Advanced mode toggle for master admin
        const advancedToggle = document.getElementById('toggleAdvancedMode');
        if (advancedToggle) {
            advancedToggle.addEventListener('click', () => this.toggleAdvancedMode());
        }
    }
    
    async checkUserRole() {
        try {
            const response = await fetch('/api/me');
            if (response.ok) {
                const user = await response.json();
                this.userRole = user.role;
                
                // Show advanced mode toggle for master admin
                if (this.userRole === 'master_admin') {
                    const advancedToggleDiv = document.getElementById('advancedModeToggle');
                    if (advancedToggleDiv) {
                        advancedToggleDiv.style.display = 'block';
                    }
                }
            }
        } catch (error) {
            console.error('Failed to check user role:', error);
        }
        
        // Show welcome message after checking role
        this.showWelcomeMessage();
    }
    
    toggleAdvancedMode() {
        this.advancedMode = !this.advancedMode;
        const button = document.getElementById('toggleAdvancedMode');
        const indicator = document.getElementById('advancedModeIndicator');
        
        if (this.advancedMode) {
            button.textContent = '🔒 Disable Advanced Mode';
            button.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
            indicator.style.display = 'block';
            
            this.addMessage('assistant', 
                '⚡ **Advanced Mode Enabled**\n\n' +
                'I can now help you with:\n' +
                '• Code analysis and modifications\n' +
                '• System-level operations\n' +
                '• Database queries and updates\n' +
                '• Advanced troubleshooting\n\n' +
                '⚠️ Use with caution - changes can affect the system.'
            );
        } else {
            button.textContent = '🔓 Enable Advanced Mode';
            button.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
            indicator.style.display = 'none';
            
            this.addMessage('assistant', 
                'Advanced Mode disabled. I\'m back to regular assistance mode.'
            );
        }
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
            let welcomeMsg = 'Hello! 👋 I\'m your AI assistant for VZT Accounting. I can help you with:\n\n' +
                '• Understanding features\n' +
                '• Invoice management\n' +
                '• Cash flow projections\n' +
                '• User roles & permissions\n' +
                '• QuickBooks integration\n\n';
            
            if (this.userRole === 'master_admin') {
                welcomeMsg += '🔐 **Master Admin Access**\n' +
                    'You can enable Advanced Mode to access:\n' +
                    '• Code analysis & modifications\n' +
                    '• System-level operations\n' +
                    '• Advanced troubleshooting\n\n';
            }
            
            welcomeMsg += 'What would you like to know?';
            
            this.addMessage('assistant', welcomeMsg);
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
        
        // Simple markdown-like formatting
        let formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // **bold**
            .replace(/\n/g, '<br>');  // newlines
        
        contentDiv.innerHTML = formattedContent;
        
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
            // Check if advanced mode and message contains action keywords
            const isActionRequest = this.advancedMode && (
                message.toLowerCase().includes('analyze') ||
                message.toLowerCase().includes('modify') ||
                message.toLowerCase().includes('change code') ||
                message.toLowerCase().includes('update code') ||
                message.toLowerCase().includes('fix') ||
                message.toLowerCase().includes('execute')
            );
            
            if (isActionRequest && this.userRole === 'master_admin') {
                // Use advanced AI action endpoint
                const response = await fetch('/api/ai/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'advanced_query',
                        parameters: {
                            message: message,
                            history: this.conversationHistory.slice(-10)
                        }
                    })
                });
                
                this.hideTypingIndicator();
                
                if (!response.ok) {
                    throw new Error('Failed to execute advanced action');
                }
                
                const data = await response.json();
                if (data.success) {
                    this.addMessage('assistant', data.message || 'Action completed successfully.');
                } else {
                    this.addMessage('assistant', data.message || data.error || 'Action failed.');
                }
            } else {
                // Use regular chat endpoint
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
            }
            
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
