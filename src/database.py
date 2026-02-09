import sqlite3
import json
import logging
from datetime import datetime
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
