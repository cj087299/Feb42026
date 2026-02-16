"""Enhanced error handling and logging system for VZT Accounting.

Provides comprehensive error tracking, logging, and reporting capabilities,
especially for advanced AI operations.
"""

import logging
import traceback
import json
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, session
import os


class ErrorLogger:
    """Enhanced error logging with file and database persistence."""
    
    def __init__(self, log_dir: str = 'logs'):
        """Initialize error logger.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = log_dir
        self.ensure_log_dir()
        self.setup_logging()
    
    def ensure_log_dir(self):
        """Ensure log directory exists."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def setup_logging(self):
        """Setup enhanced logging configuration."""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Error log file - for errors only
        error_handler = logging.FileHandler(
            os.path.join(self.log_dir, 'errors.log')
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # AI operations log file - for AI-specific operations
        ai_handler = logging.FileHandler(
            os.path.join(self.log_dir, 'ai_operations.log')
        )
        ai_handler.setLevel(logging.INFO)
        ai_handler.setFormatter(detailed_formatter)
        
        # Add handlers to root logger
        logging.getLogger().addHandler(error_handler)
        
        # Create AI-specific logger
        ai_logger = logging.getLogger('ai_operations')
        ai_logger.addHandler(ai_handler)
        ai_logger.setLevel(logging.INFO)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                  user_id: Optional[int] = None, user_email: Optional[str] = None) -> Dict[str, Any]:
        """Log an error with full context.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            user_id: User ID if available
            user_email: User email if available
            
        Returns:
            Dict containing error details
        """
        error_details = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'user_id': user_id,
            'user_email': user_email,
            'context': context or {}
        }
        
        # Log to file
        logger = logging.getLogger('errors')
        logger.error(f"Error occurred: {json.dumps(error_details, indent=2)}")
        
        return error_details
    
    def log_ai_operation(self, operation: str, details: Dict[str, Any],
                         user_id: Optional[int] = None, user_email: Optional[str] = None,
                         success: bool = True, error: Optional[str] = None):
        """Log an AI operation (especially for advanced mode).
        
        Args:
            operation: Name of the operation
            details: Operation details
            user_id: User ID
            user_email: User email
            success: Whether operation succeeded
            error: Error message if failed
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'user_id': user_id,
            'user_email': user_email,
            'success': success,
            'details': details,
            'error': error
        }
        
        ai_logger = logging.getLogger('ai_operations')
        if success:
            ai_logger.info(f"AI Operation: {json.dumps(log_entry, indent=2)}")
        else:
            ai_logger.error(f"AI Operation Failed: {json.dumps(log_entry, indent=2)}")
    
    def get_recent_errors(self, limit: int = 100) -> list:
        """Get recent errors from log file.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent errors
        """
        errors = []
        error_log_path = os.path.join(self.log_dir, 'errors.log')
        
        if not os.path.exists(error_log_path):
            return errors
        
        try:
            with open(error_log_path, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-limit:]:
                    if line.strip():
                        errors.append(line.strip())
        except Exception as e:
            logging.error(f"Failed to read error log: {e}")
        
        return errors
    
    def get_ai_operation_logs(self, limit: int = 100) -> list:
        """Get recent AI operation logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of recent AI operations
        """
        logs = []
        ai_log_path = os.path.join(self.log_dir, 'ai_operations.log')
        
        if not os.path.exists(ai_log_path):
            return logs
        
        try:
            with open(ai_log_path, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-limit:]:
                    if line.strip():
                        logs.append(line.strip())
        except Exception as e:
            logging.error(f"Failed to read AI operations log: {e}")
        
        return logs


def handle_errors(operation_name: str = None):
    """Decorator for comprehensive error handling.
    
    Args:
        operation_name: Name of the operation being performed
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Log the error
                from main import error_logger
                
                context = {
                    'operation': operation_name or f.__name__,
                    'args': str(args)[:200],  # Limit size
                    'kwargs': str(kwargs)[:200],
                    'request_path': request.path if request else None,
                    'request_method': request.method if request else None,
                    'ip_address': request.remote_addr if request else None
                }
                
                user_id = session.get('user_id') if session else None
                user_email = session.get('user_email') if session else None
                
                error_details = error_logger.log_error(
                    e, context, user_id, user_email
                )
                
                # Re-raise the exception
                raise
        return wrapped
    return decorator


def log_ai_action(action_type: str):
    """Decorator to log AI actions (especially for master admin advanced mode).
    
    Args:
        action_type: Type of AI action
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from main import error_logger
            
            user_id = session.get('user_id') if session else None
            user_email = session.get('user_email') if session else None
            
            # Log operation start
            details = {
                'action_type': action_type,
                'function': f.__name__,
                'request_data': str(request.get_json() if request and request.is_json else {})[:500]
            }
            
            try:
                result = f(*args, **kwargs)
                
                # Log success
                error_logger.log_ai_operation(
                    operation=action_type,
                    details=details,
                    user_id=user_id,
                    user_email=user_email,
                    success=True
                )
                
                return result
            except Exception as e:
                # Log failure
                error_logger.log_ai_operation(
                    operation=action_type,
                    details=details,
                    user_id=user_id,
                    user_email=user_email,
                    success=False,
                    error=str(e)
                )
                
                raise
        return wrapped
    return decorator
