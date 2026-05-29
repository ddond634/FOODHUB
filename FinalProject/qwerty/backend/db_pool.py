"""
Database Connection Pool and Safe Query Utilities
Provides connection pooling, transaction management, and safe query execution
"""
import os
import sqlite3
import pymysql
from contextlib import contextmanager
from threading import Lock
import queue
from dotenv import load_dotenv

load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

class DatabasePool:
    """Simple connection pool for database connections"""
    
    def __init__(self, min_connections=2, max_connections=10):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = queue.Queue(maxsize=max_connections)
        self.lock = Lock()
        self.connection_count = 0
        
        # Initialize minimum connections
        for _ in range(min_connections):
            self.pool.put(self._create_connection())
            self.connection_count += 1
    
    def _create_connection(self):
        """Create a new database connection"""
        if DB_ENGINE == 'mysql':
            conn = pymysql.connect(
                host=os.environ.get('DB_HOST', '127.0.0.1'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASS', ''),
                db=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', '3306')),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                charset='utf8mb4'
            )
        else:
            conn = sqlite3.connect('qwerty.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Enable foreign keys
            conn.execute('PRAGMA foreign_keys = ON')
        
        return conn
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            # Try to get a connection from the pool (non-blocking)
            conn = self.pool.get_nowait()
            
            # Test if connection is still alive
            try:
                if DB_ENGINE == 'mysql':
                    conn.ping(reconnect=True)
                else:
                    conn.execute('SELECT 1')
                return conn
            except:
                # Connection is dead, create a new one
                return self._create_connection()
        except queue.Empty:
            # Pool is empty, create a new connection if under max
            with self.lock:
                if self.connection_count < self.max_connections:
                    self.connection_count += 1
                    return self._create_connection()
            
            # Wait for a connection to become available
            return self.pool.get()
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            self.pool.put_nowait(conn)
        except queue.Full:
            # Pool is full, close the connection
            try:
                conn.close()
            except:
                pass
            with self.lock:
                self.connection_count -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except:
                pass
        self.connection_count = 0


# Global connection pool
_db_pool = None

def get_db_pool():
    """Get the global database pool"""
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool


@contextmanager
def get_db_connection():
    """
    Context manager for database connections
    Automatically handles connection pooling and cleanup
    
    Usage:
        with get_db_connection() as (conn, cursor):
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """
    pool = get_db_pool()
    conn = pool.get_connection()
    cursor = conn.cursor()
    
    try:
        yield conn, cursor
    finally:
        cursor.close()
        pool.return_connection(conn)


@contextmanager
def transaction():
    """
    Context manager for database transactions
    Automatically commits on success, rolls back on error
    
    Usage:
        with transaction() as (conn, cursor):
            cursor.execute("INSERT INTO users ...")
            cursor.execute("UPDATE products ...")
            # Automatically commits when exiting context
    """
    pool = get_db_pool()
    conn = pool.get_connection()
    cursor = conn.cursor()
    
    try:
        yield conn, cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        pool.return_connection(conn)


class SafeQuery:
    """Safe query builder with parameterization"""
    
    @staticmethod
    def select(table, columns='*', where=None, order_by=None, limit=None):
        """
        Build a safe SELECT query
        
        Args:
            table: Table name
            columns: Column names (string or list)
            where: Dictionary of conditions {column: value}
            order_by: Column name or list of tuples (column, 'ASC'/'DESC')
            limit: Integer limit
        
        Returns:
            (query, params) tuple
        """
        if isinstance(columns, list):
            columns = ', '.join(columns)
        
        query = f"SELECT {columns} FROM {table}"
        params = []
        
        if where:
            conditions = []
            for col, val in where.items():
                if DB_ENGINE == 'mysql':
                    conditions.append(f"{col} = %s")
                else:
                    conditions.append(f"{col} = ?")
                params.append(val)
            
            query += " WHERE " + " AND ".join(conditions)
        
        if order_by:
            if isinstance(order_by, str):
                query += f" ORDER BY {order_by}"
            elif isinstance(order_by, list):
                order_parts = [f"{col} {direction}" for col, direction in order_by]
                query += " ORDER BY " + ", ".join(order_parts)
        
        if limit:
            query += f" LIMIT {int(limit)}"
        
        return query, params
    
    @staticmethod
    def insert(table, data):
        """
        Build a safe INSERT query
        
        Args:
            table: Table name
            data: Dictionary of {column: value}
        
        Returns:
            (query, params) tuple
        """
        columns = ', '.join(data.keys())
        
        if DB_ENGINE == 'mysql':
            placeholders = ', '.join(['%s'] * len(data))
        else:
            placeholders = ', '.join(['?'] * len(data))
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        params = list(data.values())
        
        return query, params
    
    @staticmethod
    def update(table, data, where):
        """
        Build a safe UPDATE query
        
        Args:
            table: Table name
            data: Dictionary of {column: value} to update
            where: Dictionary of conditions {column: value}
        
        Returns:
            (query, params) tuple
        """
        set_parts = []
        params = []
        
        for col, val in data.items():
            if DB_ENGINE == 'mysql':
                set_parts.append(f"{col} = %s")
            else:
                set_parts.append(f"{col} = ?")
            params.append(val)
        
        query = f"UPDATE {table} SET " + ", ".join(set_parts)
        
        if where:
            conditions = []
            for col, val in where.items():
                if DB_ENGINE == 'mysql':
                    conditions.append(f"{col} = %s")
                else:
                    conditions.append(f"{col} = ?")
                params.append(val)
            
            query += " WHERE " + " AND ".join(conditions)
        
        return query, params
    
    @staticmethod
    def delete(table, where):
        """
        Build a safe DELETE query
        
        Args:
            table: Table name
            where: Dictionary of conditions {column: value}
        
        Returns:
            (query, params) tuple
        """
        query = f"DELETE FROM {table}"
        params = []
        
        if where:
            conditions = []
            for col, val in where.items():
                if DB_ENGINE == 'mysql':
                    conditions.append(f"{col} = %s")
                else:
                    conditions.append(f"{col} = ?")
                params.append(val)
            
            query += " WHERE " + " AND ".join(conditions)
        
        return query, params


def execute_query(query, params=None, fetch='all'):
    """
    Execute a query safely with automatic connection management
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or list)
        fetch: 'all', 'one', or None
    
    Returns:
        Query results or None
    """
    with get_db_connection() as (conn, cursor):
        cursor.execute(query, params or ())
        
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:
            return None


def execute_transaction(queries):
    """
    Execute multiple queries in a transaction
    
    Args:
        queries: List of (query, params) tuples
    
    Returns:
        List of results
    """
    with transaction() as (conn, cursor):
        results = []
        for query, params in queries:
            cursor.execute(query, params or ())
            results.append(cursor.fetchall())
        return results


# Export commonly used functions
__all__ = [
    'DatabasePool',
    'get_db_pool',
    'get_db_connection',
    'transaction',
    'SafeQuery',
    'execute_query',
    'execute_transaction',
    'DB_ENGINE'
]
