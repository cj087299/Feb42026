import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class Database:
    """Manages database for VZT Accounting data.
    
    Supports both SQLite (for local/dev) and Google Cloud SQL (for production).
    """
    
    def __init__(self, db_path: str = 'vzt_accounting.db'):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file, or connection string for Cloud SQL
        """
        self.db_path = db_path
        self.use_cloud_sql = os.environ.get('USE_CLOUD_SQL', 'false').lower() == 'true'
        self.cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME', 
            'project-df2be397-d2f7-4b71-944:us-south1:companydatabase2-4-26')
        self.db_name = os.environ.get('CLOUD_SQL_DATABASE_NAME', 'accounting_app')
        self.db_user = os.environ.get('CLOUD_SQL_USER', 'root')
        self.db_password = os.environ.get('CLOUD_SQL_PASSWORD', '')
        
        self.init_database()
    
    def get_connection(self):
        """Get a database connection (SQLite or Cloud SQL)."""
        if self.use_cloud_sql:
            try:
                # Import Cloud SQL connector
                from google.cloud.sql.connector import Connector
                import pymysql
                
                # Initialize Connector object
                connector = Connector()
                
                # Function to return the database connection
                conn = connector.connect(
                    self.cloud_sql_connection_name,
                    "pymysql",
                    user=self.db_user,
                    password=self.db_password,
                    db=self.db_name
                )
                logger.info(f"Connected to Cloud SQL: {self.cloud_sql_connection_name}")
                return conn
            except ImportError:
                logger.error("cloud-sql-python-connector or pymysql not installed. Falling back to SQLite.")
                self.use_cloud_sql = False
                return sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"Failed to connect to Cloud SQL: {e}. Falling back to SQLite.")
                self.use_cloud_sql = False
                return sqlite3.connect(self.db_path)
        else:
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_cloud_sql:
            # MySQL/Cloud SQL syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_metadata (
                    invoice_id VARCHAR(255) PRIMARY KEY,
                    vzt_rep VARCHAR(255),
                    sent_to_vzt_rep_date VARCHAR(50),
                    customer_portal VARCHAR(255),
                    customer_portal_submission_date VARCHAR(50),
                    created_at VARCHAR(50),
                    updated_at VARCHAR(50)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_cash_flows (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    flow_type VARCHAR(50) NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    date VARCHAR(50),
                    description TEXT,
                    is_recurring TINYINT DEFAULT 0,
                    recurrence_type VARCHAR(50),
                    recurrence_interval INT,
                    recurrence_start_date VARCHAR(50),
                    recurrence_end_date VARCHAR(50),
                    created_at VARCHAR(50),
                    updated_at VARCHAR(50)
                )
            ''')
            
            # User management tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    role VARCHAR(50) NOT NULL,
                    is_active TINYINT DEFAULT 1,
                    created_at VARCHAR(50),
                    updated_at VARCHAR(50),
                    last_login VARCHAR(50)
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    user_email VARCHAR(255),
                    action VARCHAR(255) NOT NULL,
                    resource_type VARCHAR(100),
                    resource_id VARCHAR(255),
                    details TEXT,
                    ip_address VARCHAR(50),
                    user_agent TEXT,
                    timestamp VARCHAR(50) NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Password reset tokens table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at VARCHAR(50) NOT NULL,
                    used TINYINT DEFAULT 0,
                    created_at VARCHAR(50) NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # QBO tokens table for centralized credential management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS qbo_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    client_secret TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    access_token TEXT,
                    realm_id VARCHAR(255) NOT NULL,
                    access_token_expires_at VARCHAR(50),
                    refresh_token_expires_at VARCHAR(50),
                    created_by_user_id INT,
                    created_at VARCHAR(50) NOT NULL,
                    updated_at VARCHAR(50) NOT NULL,
                    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
                )
            ''')
        else:
            # SQLite syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_metadata (
                    invoice_id TEXT PRIMARY KEY,
                    vzt_rep TEXT,
                    sent_to_vzt_rep_date TEXT,
                    customer_portal TEXT,
                    customer_portal_submission_date TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_cash_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flow_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT,
                    description TEXT,
                    is_recurring INTEGER DEFAULT 0,
                    recurrence_type TEXT,
                    recurrence_interval INTEGER,
                    recurrence_start_date TEXT,
                    recurrence_end_date TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # User management tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT,
                    last_login TEXT
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_email TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Password reset tokens table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # QBO tokens table for centralized credential management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS qbo_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    client_secret TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    access_token TEXT,
                    realm_id TEXT NOT NULL,
                    access_token_expires_at TEXT,
                    refresh_token_expires_at TEXT,
                    created_by_user_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
                )
            ''')
        
        conn.commit()
        conn.close()
        
        db_type = "Cloud SQL" if self.use_cloud_sql else "SQLite"
        db_location = self.cloud_sql_connection_name if self.use_cloud_sql else self.db_path
        logger.info(f"Database initialized using {db_type} at {db_location}")
    
    # Invoice metadata methods
    
    def save_invoice_metadata(self, invoice_id: str, metadata: Dict) -> bool:
        """Save or update invoice metadata."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            if self.use_cloud_sql:
                # MySQL syntax with ON DUPLICATE KEY UPDATE
                cursor.execute('''
                    INSERT INTO invoice_metadata 
                    (invoice_id, vzt_rep, sent_to_vzt_rep_date, customer_portal, 
                     customer_portal_submission_date, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        vzt_rep = VALUES(vzt_rep),
                        sent_to_vzt_rep_date = VALUES(sent_to_vzt_rep_date),
                        customer_portal = VALUES(customer_portal),
                        customer_portal_submission_date = VALUES(customer_portal_submission_date),
                        updated_at = VALUES(updated_at)
                ''', (
                    invoice_id,
                    metadata.get('vzt_rep'),
                    metadata.get('sent_to_vzt_rep_date'),
                    metadata.get('customer_portal'),
                    metadata.get('customer_portal_submission_date'),
                    now,
                    now
                ))
            else:
                # SQLite syntax
                cursor.execute('''
                    INSERT INTO invoice_metadata 
                    (invoice_id, vzt_rep, sent_to_vzt_rep_date, customer_portal, 
                     customer_portal_submission_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(invoice_id) DO UPDATE SET
                        vzt_rep = excluded.vzt_rep,
                        sent_to_vzt_rep_date = excluded.sent_to_vzt_rep_date,
                        customer_portal = excluded.customer_portal,
                        customer_portal_submission_date = excluded.customer_portal_submission_date,
                        updated_at = excluded.updated_at
                ''', (
                    invoice_id,
                    metadata.get('vzt_rep'),
                    metadata.get('sent_to_vzt_rep_date'),
                    metadata.get('customer_portal'),
                    metadata.get('customer_portal_submission_date'),
                    now,
                    now
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved metadata for invoice {invoice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save invoice metadata: {e}")
            return False
    
    def get_invoice_metadata(self, invoice_id: str) -> Optional[Dict]:
        """Get metadata for a specific invoice."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'''
                SELECT invoice_id, vzt_rep, sent_to_vzt_rep_date, customer_portal,
                       customer_portal_submission_date, created_at, updated_at
                FROM invoice_metadata
                WHERE invoice_id = {placeholder}
            ''', (invoice_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'invoice_id': row[0],
                    'vzt_rep': row[1],
                    'sent_to_vzt_rep_date': row[2],
                    'customer_portal': row[3],
                    'customer_portal_submission_date': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get invoice metadata: {e}")
            return None
    
    def get_all_invoice_metadata(self) -> List[Dict]:
        """Get all invoice metadata."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT invoice_id, vzt_rep, sent_to_vzt_rep_date, customer_portal,
                       customer_portal_submission_date, created_at, updated_at
                FROM invoice_metadata
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'invoice_id': row[0],
                'vzt_rep': row[1],
                'sent_to_vzt_rep_date': row[2],
                'customer_portal': row[3],
                'customer_portal_submission_date': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all invoice metadata: {e}")
            return []
    
    # Custom cash flow methods
    
    def add_custom_cash_flow(self, flow_data: Dict) -> Optional[int]:
        """Add a custom cash flow (inflow or outflow)."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 11)
            
            cursor.execute(f'''
                INSERT INTO custom_cash_flows
                (flow_type, amount, date, description, is_recurring, recurrence_type,
                 recurrence_interval, recurrence_start_date, recurrence_end_date,
                 created_at, updated_at)
                VALUES ({placeholders})
            ''', (
                flow_data.get('flow_type'),
                flow_data.get('amount'),
                flow_data.get('date'),
                flow_data.get('description'),
                1 if flow_data.get('is_recurring') else 0,
                flow_data.get('recurrence_type'),
                flow_data.get('recurrence_interval'),
                flow_data.get('recurrence_start_date'),
                flow_data.get('recurrence_end_date'),
                now,
                now
            ))
            
            flow_id = cursor.lastrowid
            conn.commit()
            conn.close()
            logger.info(f"Added custom cash flow with ID {flow_id}")
            return flow_id
        except Exception as e:
            logger.error(f"Failed to add custom cash flow: {e}")
            return None
    
    def get_custom_cash_flows(self, flow_type: Optional[str] = None) -> List[Dict]:
        """Get all custom cash flows, optionally filtered by type."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            
            if flow_type:
                cursor.execute(f'''
                    SELECT id, flow_type, amount, date, description, is_recurring,
                           recurrence_type, recurrence_interval, recurrence_start_date,
                           recurrence_end_date, created_at, updated_at
                    FROM custom_cash_flows
                    WHERE flow_type = {placeholder}
                    ORDER BY date
                ''', (flow_type,))
            else:
                cursor.execute('''
                    SELECT id, flow_type, amount, date, description, is_recurring,
                           recurrence_type, recurrence_interval, recurrence_start_date,
                           recurrence_end_date, created_at, updated_at
                    FROM custom_cash_flows
                    ORDER BY date
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'flow_type': row[1],
                'amount': float(row[2]) if row[2] else 0,
                'date': row[3],
                'description': row[4],
                'is_recurring': bool(row[5]),
                'recurrence_type': row[6],
                'recurrence_interval': row[7],
                'recurrence_start_date': row[8],
                'recurrence_end_date': row[9],
                'created_at': row[10],
                'updated_at': row[11]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get custom cash flows: {e}")
            return []
    
    def update_custom_cash_flow(self, flow_id: int, flow_data: Dict) -> bool:
        """Update an existing custom cash flow."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 10)
            
            cursor.execute(f'''
                UPDATE custom_cash_flows
                SET flow_type = {placeholder}, amount = {placeholder}, date = {placeholder}, 
                    description = {placeholder}, is_recurring = {placeholder}, 
                    recurrence_type = {placeholder}, recurrence_interval = {placeholder},
                    recurrence_start_date = {placeholder}, recurrence_end_date = {placeholder}, 
                    updated_at = {placeholder}
                WHERE id = {placeholder}
            ''', (
                flow_data.get('flow_type'),
                flow_data.get('amount'),
                flow_data.get('date'),
                flow_data.get('description'),
                1 if flow_data.get('is_recurring') else 0,
                flow_data.get('recurrence_type'),
                flow_data.get('recurrence_interval'),
                flow_data.get('recurrence_start_date'),
                flow_data.get('recurrence_end_date'),
                now,
                flow_id
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Updated custom cash flow {flow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update custom cash flow: {e}")
            return False
    
    def delete_custom_cash_flow(self, flow_id: int) -> bool:
        """Delete a custom cash flow."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'DELETE FROM custom_cash_flows WHERE id = {placeholder}', (flow_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Deleted custom cash flow {flow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete custom cash flow: {e}")
            return False
    
    # User management methods
    
    def create_user(self, email: str, password_hash: str, full_name: str, role: str) -> Optional[int]:
        """Create a new user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 6)
            
            cursor.execute(f'''
                INSERT INTO users (email, password_hash, full_name, role, created_at, updated_at)
                VALUES ({placeholders})
            ''', (email, password_hash, full_name, role, now, now))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            logger.info(f"Created user {email} with ID {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'''
                SELECT id, email, password_hash, full_name, role, is_active, created_at, updated_at, last_login
                FROM users
                WHERE email = {placeholder}
            ''', (email,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'password_hash': row[2],
                    'full_name': row[3],
                    'role': row[4],
                    'is_active': bool(row[5]),
                    'created_at': row[6],
                    'updated_at': row[7],
                    'last_login': row[8]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'''
                SELECT id, email, password_hash, full_name, role, is_active, created_at, updated_at, last_login
                FROM users
                WHERE id = {placeholder}
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'email': row[1],
                    'password_hash': row[2],
                    'full_name': row[3],
                    'role': row[4],
                    'is_active': bool(row[5]),
                    'created_at': row[6],
                    'updated_at': row[7],
                    'last_login': row[8]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, full_name, role, is_active, created_at, updated_at, last_login
                FROM users
                ORDER BY created_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'email': row[1],
                'full_name': row[2],
                'role': row[3],
                'is_active': bool(row[4]),
                'created_at': row[5],
                'updated_at': row[6],
                'last_login': row[7]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    def update_user(self, user_id: int, data: Dict) -> bool:
        """Update user information."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            placeholder = '%s' if self.use_cloud_sql else '?'
            
            fields = []
            values = []
            
            if 'email' in data:
                fields.append(f'email = {placeholder}')
                values.append(data['email'])
            if 'full_name' in data:
                fields.append(f'full_name = {placeholder}')
                values.append(data['full_name'])
            if 'role' in data:
                fields.append(f'role = {placeholder}')
                values.append(data['role'])
            if 'is_active' in data:
                fields.append(f'is_active = {placeholder}')
                values.append(1 if data['is_active'] else 0)
            if 'password_hash' in data:
                fields.append(f'password_hash = {placeholder}')
                values.append(data['password_hash'])
            
            fields.append(f'updated_at = {placeholder}')
            values.append(now)
            values.append(user_id)
            
            cursor.execute(f'''
                UPDATE users
                SET {', '.join(fields)}
                WHERE id = {placeholder}
            ''', tuple(values))
            
            conn.commit()
            conn.close()
            logger.info(f"Updated user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login time."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            placeholder = '%s' if self.use_cloud_sql else '?'
            
            cursor.execute(f'''
                UPDATE users
                SET last_login = {placeholder}
                WHERE id = {placeholder}
            ''', (now, user_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'DELETE FROM users WHERE id = {placeholder}', (user_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Deleted user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False
    
    # Audit log methods
    
    def log_audit(self, user_id: Optional[int], user_email: Optional[str], action: str, 
                   resource_type: Optional[str] = None, resource_id: Optional[str] = None,
                   details: Optional[str] = None, ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> Optional[int]:
        """Log an audit entry."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 8)
            
            cursor.execute(f'''
                INSERT INTO audit_log
                (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent, timestamp)
                VALUES ({placeholders}, {placeholder})
            ''', (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent, now))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return log_id
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
            return None
    
    def get_audit_logs(self, user_id: Optional[int] = None, action: Optional[str] = None,
                       resource_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get audit logs with optional filters."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT id, user_id, user_email, action, resource_type, resource_id, 
                       details, ip_address, user_agent, timestamp
                FROM audit_log
            '''
            
            conditions = []
            values = []
            placeholder = '%s' if self.use_cloud_sql else '?'
            
            if user_id:
                conditions.append(f'user_id = {placeholder}')
                values.append(user_id)
            if action:
                conditions.append(f'action = {placeholder}')
                values.append(action)
            if resource_type:
                conditions.append(f'resource_type = {placeholder}')
                values.append(resource_type)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += f' ORDER BY timestamp DESC LIMIT {placeholder}'
            values.append(limit)
            
            cursor.execute(query, tuple(values))
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'user_id': row[1],
                'user_email': row[2],
                'action': row[3],
                'resource_type': row[4],
                'resource_id': row[5],
                'details': row[6],
                'ip_address': row[7],
                'user_agent': row[8],
                'timestamp': row[9]
            } for row in rows]
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []
    
    # Password reset token methods
    
    def create_password_reset_token(self, user_id: int, token: str, expires_at: str) -> Optional[int]:
        """Create a password reset token."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 4)
            
            cursor.execute(f'''
                INSERT INTO password_reset_tokens
                (user_id, token, expires_at, created_at)
                VALUES ({placeholders})
            ''', (user_id, token, expires_at, now))
            
            token_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return token_id
        except Exception as e:
            logger.error(f"Failed to create password reset token: {e}")
            return None
    
    def get_password_reset_token(self, token: str) -> Optional[Dict]:
        """Get password reset token details."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'''
                SELECT id, user_id, token, expires_at, used, created_at
                FROM password_reset_tokens
                WHERE token = {placeholder}
            ''', (token,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'token': row[2],
                    'expires_at': row[3],
                    'used': bool(row[4]),
                    'created_at': row[5]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get password reset token: {e}")
            return None
    
    def mark_token_as_used(self, token: str) -> bool:
        """Mark a password reset token as used."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            cursor.execute(f'''
                UPDATE password_reset_tokens
                SET used = 1
                WHERE token = {placeholder}
            ''', (token,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to mark token as used: {e}")
            return False
    
    # QBO Token Management Methods
    
    def save_qbo_credentials(self, credentials: Dict, created_by_user_id: Optional[int] = None) -> bool:
        """Save or update QBO credentials in the database.
        
        Args:
            credentials: Dictionary containing QBO credentials
                - client_id: OAuth Client ID
                - client_secret: OAuth Client Secret
                - refresh_token: Long-lived refresh token
                - access_token: Short-lived access token (optional)
                - realm_id: QuickBooks Company ID
                - expires_in: Seconds until access token expires (optional, default 3600)
                - x_refresh_token_expires_in: Seconds until refresh token expires (optional, default 8726400)
            created_by_user_id: ID of the user who is setting these credentials
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Calculate token expiration times from QBO response
            # Access token typically expires in 1 hour (3600 seconds)
            expires_in = credentials.get('expires_in', 3600)
            access_token_expires = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            # Refresh token expires in 101 days (8726400 seconds)
            refresh_expires_in = credentials.get('x_refresh_token_expires_in', 8726400)
            refresh_token_expires = (datetime.now() + timedelta(seconds=refresh_expires_in)).isoformat()
            
            # First, delete any existing credentials (we only keep one set)
            cursor.execute('DELETE FROM qbo_tokens')
            
            # Insert new credentials
            placeholder = '%s' if self.use_cloud_sql else '?'
            placeholders = ', '.join([placeholder] * 10)
            
            cursor.execute(f'''
                INSERT INTO qbo_tokens
                (client_id, client_secret, refresh_token, access_token, realm_id,
                 access_token_expires_at, refresh_token_expires_at, created_by_user_id,
                 created_at, updated_at)
                VALUES ({placeholders})
            ''', (
                credentials.get('client_id'),
                credentials.get('client_secret'),
                credentials.get('refresh_token'),
                credentials.get('access_token'),
                credentials.get('realm_id'),
                access_token_expires,
                refresh_token_expires,
                created_by_user_id,
                now,
                now
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved QBO credentials to database")
            return True
        except Exception as e:
            logger.error(f"Failed to save QBO credentials: {e}")
            return False
    
    def get_qbo_credentials(self) -> Optional[Dict]:
        """Get the current QBO credentials from the database.
        
        Returns:
            Dictionary with QBO credentials or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, client_id, client_secret, refresh_token, access_token, realm_id,
                       access_token_expires_at, refresh_token_expires_at, created_by_user_id,
                       created_at, updated_at
                FROM qbo_tokens
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'client_id': row[1],
                    'client_secret': row[2],
                    'refresh_token': row[3],
                    'access_token': row[4],
                    'realm_id': row[5],
                    'access_token_expires_at': row[6],
                    'refresh_token_expires_at': row[7],
                    'created_by_user_id': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get QBO credentials: {e}")
            return None
    
    def update_qbo_tokens(self, access_token: str, refresh_token: Optional[str] = None, 
                          expires_in: int = 3600, x_refresh_token_expires_in: int = 8726400) -> bool:
        """Update QBO access token and optionally refresh token.
        
        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Seconds until access token expires (default: 3600)
            x_refresh_token_expires_in: Seconds until refresh token expires (default: 8726400)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            access_token_expires = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            placeholder = '%s' if self.use_cloud_sql else '?'
            
            if refresh_token:
                # Update both tokens
                refresh_token_expires = (datetime.now() + timedelta(seconds=x_refresh_token_expires_in)).isoformat()
                cursor.execute(f'''
                    UPDATE qbo_tokens
                    SET access_token = {placeholder},
                        refresh_token = {placeholder},
                        access_token_expires_at = {placeholder},
                        refresh_token_expires_at = {placeholder},
                        updated_at = {placeholder}
                    WHERE id = (SELECT id FROM qbo_tokens ORDER BY created_at DESC LIMIT 1)
                ''', (access_token, refresh_token, access_token_expires, refresh_token_expires, now))
            else:
                # Update only access token
                cursor.execute(f'''
                    UPDATE qbo_tokens
                    SET access_token = {placeholder},
                        access_token_expires_at = {placeholder},
                        updated_at = {placeholder}
                    WHERE id = (SELECT id FROM qbo_tokens ORDER BY created_at DESC LIMIT 1)
                ''', (access_token, access_token_expires, now))
            
            conn.commit()
            conn.close()
            logger.info("Updated QBO tokens in database")
            return True
        except Exception as e:
            logger.error(f"Failed to update QBO tokens: {e}")
            return False
