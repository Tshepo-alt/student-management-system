// frontend/js/chatbot.js
class ChatbotWidget {
    constructor() {
        this.isOpen = false;
        this.studentInfo = null;
        this.init();
    }
    
    init() {
        this.createWidget();
        this.loadStudentInfo();
        this.addEventListeners();
    }
    
    createWidget() {
        // Create chatbot container
        const chatbotHTML = `
            <div id="chatbot-widget" class="chatbot-widget">
                <div class="chatbot-header" id="chatbot-header">
                    <div class="chatbot-title">
                        <span>🎓 Student Support Assistant</span>
                    </div>
                    <button class="chatbot-toggle" id="chatbot-toggle">💬</button>
                </div>
                <div class="chatbot-container" id="chatbot-container" style="display: none;">
                    <div class="chatbot-messages" id="chatbot-messages">
                        <div class="message bot-message">
                            Hello! I'm your Student Support Assistant. I can help with access issues, login problems, and create support tickets. How can I help you today?
                        </div>
                    </div>
                    <div class="chatbot-input-area">
                        <textarea id="chatbot-input" placeholder="Type your message here..." rows="2"></textarea>
                        <button id="chatbot-send" class="send-btn">Send</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    }
    
    loadStudentInfo() {
        // Get student info from your system (adjust based on your auth system)
        this.studentInfo = {
            student_id: localStorage.getItem('student_id') || null,
            student_name: localStorage.getItem('student_name') || null,
            student_email: localStorage.getItem('student_email') || null
        };
    }
    
    addEventListeners() {
        const toggleBtn = document.getElementById('chatbot-toggle');
        const container = document.getElementById('chatbot-container');
        const sendBtn = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');
        
        toggleBtn.addEventListener('click', () => {
            this.isOpen = !this.isOpen;
            container.style.display = this.isOpen ? 'flex' : 'none';
        });
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        input.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/chatbot/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    student_id: this.studentInfo?.student_id,
                    student_name: this.studentInfo?.student_name,
                    student_email: this.studentInfo?.student_email
                })
            });
            
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add bot response
            if (data.success) {
                this.addMessage(data.response, 'bot');
                
                // If ticket was created, show ticket info
                if (data.ticket_created) {
                    this.showTicketNotification(data.ticket_id);
                }
            } else {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
            
        } catch (error) {
            console.error('Chatbot error:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I cannot connect to the server. Please check your internet connection.', 'bot');
        }
    }
    
    addMessage(text, sender) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatbot-messages');
        const indicator = document.createElement('div');
        indicator.className = 'message bot-message typing-indicator';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        messagesContainer.appendChild(indicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    showTicketNotification(ticketId) {
        const notification = document.createElement('div');
        notification.className = 'ticket-notification';
        notification.innerHTML = `
            <div class="ticket-info">
                <strong>✓ Support Ticket Created</strong><br>
                Ticket ID: #${ticketId}<br>
                You will receive an email with updates.
            </div>
        `;
        
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.appendChild(notification);
        setTimeout(() => notification.remove(), 10000);
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatbotWidget();
});