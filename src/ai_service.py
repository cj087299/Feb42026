"""AI Chat Service for VZT Accounting.

Provides two levels of AI assistance:
1. General AI: Answers questions for all authenticated users
2. Master Admin AI: Can perform actions and modify code (master admin only)
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AIService:
    """AI service for answering questions and performing actions."""
    
    def __init__(self):
        """Initialize AI service."""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.is_available = bool(self.api_key)
        
        if not self.is_available:
            logger.warning("OpenAI API key not found. AI features will be simulated.")
    
    def chat(self, message: str, conversation_history: List[Dict] = None, user_role: str = None) -> Dict:
        """Process a chat message and return AI response.
        
        Args:
            message: User's message
            conversation_history: Previous messages in the conversation
            user_role: User's role for context
            
        Returns:
            Dict with response and metadata
        """
        try:
            if conversation_history is None:
                conversation_history = []
            
            # Build system prompt based on user role
            system_prompt = self._build_system_prompt(user_role)
            
            if self.is_available:
                # Use OpenAI API
                return self._chat_with_openai(message, conversation_history, system_prompt)
            else:
                # Return simulated response
                return self._simulated_chat(message, user_role)
        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            return {
                'response': 'I apologize, but I encountered an error processing your request.',
                'error': str(e)
            }
    
    def _build_system_prompt(self, user_role: str = None) -> str:
        """Build system prompt based on user role."""
        base_prompt = """You are a helpful AI assistant for VZT Accounting, a QuickBooks Online 
cash flow projection and invoice management application.

You can help users with:
- Understanding how to use the application features
- Explaining invoice management and cash flow projections
- Answering questions about QuickBooks Online integration
- Providing guidance on accounts receivable and payable
- Explaining the cash flow calendar and custom cash flows
- Helping with user management and permissions

Be concise, friendly, and professional in your responses."""
        
        if user_role == 'master_admin':
            base_prompt += """

IMPORTANT: You are assisting a Master Admin user. In addition to answering questions,
you have advanced capabilities available when specifically requested:
- Performing administrative actions
- Analyzing and suggesting code improvements
- Explaining technical implementation details
- Providing system-level insights

However, ALWAYS confirm with the user before suggesting or implementing any changes to the system."""
        
        return base_prompt
    
    def _chat_with_openai(self, message: str, conversation_history: List[Dict], 
                          system_prompt: str) -> Dict:
        """Chat using OpenAI API."""
        try:
            import openai
            
            openai.api_key = self.api_key
            
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Limit to last 10 messages
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message['content']
            
            return {
                'response': assistant_message,
                'model': 'gpt-3.5-turbo',
                'tokens_used': response.usage.get('total_tokens', 0)
            }
        except ImportError:
            logger.warning("OpenAI package not installed. Using simulated responses.")
            return self._simulated_chat(message, None)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                'response': 'I apologize, but I encountered an error connecting to the AI service.',
                'error': str(e)
            }
    
    def _simulated_chat(self, message: str, user_role: str = None) -> Dict:
        """Provide simulated responses when OpenAI is not available."""
        message_lower = message.lower()
        
        # Define some common responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            response = "Hello! I'm the VZT Accounting AI assistant. How can I help you today?"
        
        elif any(word in message_lower for word in ['invoice', 'invoices']):
            response = """I can help you with invoices! VZT Accounting allows you to:

- View and filter invoices from QuickBooks Online
- Track VZT representative assignments
- Record customer portal submissions
- Sort by due date, amount, or customer
- Edit invoice metadata

You can access invoices from the main navigation menu. Would you like to know more about any specific feature?"""
        
        elif any(word in message_lower for word in ['cash flow', 'cashflow']):
            response = """The Cash Flow Calendar is a powerful feature that helps you:

- Project cash flow based on invoice due dates
- View daily breakdown of inflows and outflows
- Track running bank balance
- Add custom inflows and outflows (one-time or recurring)
- Filter by different flow types

The system automatically pulls your bank balance from QuickBooks Online. Would you like to know more about any specific aspect?"""
        
        elif any(word in message_lower for word in ['user', 'permission', 'role']):
            response = """VZT Accounting has five user roles:

1. Master Admin - Full system access including user management
2. Admin - All accounting functions + audit logs
3. Accounts Receivable (AR) - Invoice management + custom inflows
4. Accounts Payable (AP) - AP management + custom outflows
5. View Only - Read-only access

Each role has specific permissions to maintain security. Master admins can manage users from the Users page."""
        
        elif any(word in message_lower for word in ['help', 'how', 'what']):
            response = """I'm here to help! I can answer questions about:

• Invoice Management
• Cash Flow Projections
• User Roles and Permissions
• QuickBooks Online Integration
• Custom Cash Flows
• System Features

Just ask me anything specific about these topics!"""
        
        else:
            response = """I understand you're asking about VZT Accounting. While I'm currently in 
simulated mode (OpenAI API not configured), I can provide general information about:

- Invoice management and tracking
- Cash flow projections and calendar
- User roles and permissions
- QuickBooks Online integration
- System features and navigation

Could you please rephrase your question or ask about one of these topics?"""
        
        # Add extra note for master admin
        if user_role == 'master_admin':
            response += "\n\n*Note: As a Master Admin, you have access to advanced AI capabilities. When fully configured, I can help with code analysis and system modifications upon request.*"
        
        return {
            'response': response,
            'model': 'simulated',
            'simulated': True
        }
    
    def perform_action(self, action: str, parameters: Dict, user_role: str) -> Dict:
        """Perform an action (master admin only).
        
        Args:
            action: Action to perform
            parameters: Action parameters
            user_role: User's role (must be master_admin)
            
        Returns:
            Dict with action result
        """
        if user_role != 'master_admin':
            return {
                'success': False,
                'error': 'Only master admin can perform actions'
            }
        
        try:
            # This is a placeholder for advanced AI actions
            # In a full implementation, this could:
            # - Generate code modifications
            # - Perform database operations
            # - Execute system commands (with proper safeguards)
            # - Analyze and optimize code
            
            logger.info(f"Master admin action requested: {action} with params: {parameters}")
            
            return {
                'success': False,
                'message': 'Advanced AI actions are not yet fully implemented. This feature requires additional configuration and OpenAI API access.',
                'note': 'When fully configured, master admin can request code analysis, modifications, and system actions through the AI interface.'
            }
        except Exception as e:
            logger.error(f"Error performing action: {e}")
            return {
                'success': False,
                'error': str(e)
            }
