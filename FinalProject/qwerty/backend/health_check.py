"""
System Health Check and Monitoring
Provides endpoints for system status, health checks, and monitoring
"""
import os
import psutil
import time
from datetime import datetime
from flask import jsonify

start_time = time.time()

def get_system_health():
    """Get comprehensive system health information"""
    uptime = time.time() - start_time
    
    # CPU and Memory
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('.')
    
    # Database connection status
    db_status = check_database_connection()
    
    # Calculate health score
    health_score = calculate_health_score(cpu_percent, memory.percent, disk.percent, db_status)
    
    return {
        'status': 'healthy' if health_score >= 0.7 else 'degraded' if health_score >= 0.4 else 'unhealthy',
        'health_score': round(health_score, 2),
        'timestamp': datetime.now().isoformat(),
        'uptime_seconds': int(uptime),
        'uptime_human': format_uptime(uptime),
        'system': {
            'cpu_percent': cpu_percent,
            'memory': {
                'total_mb': round(memory.total / 1024 / 1024, 2),
                'available_mb': round(memory.available / 1024 / 1024, 2),
                'percent_used': memory.percent
            },
            'disk': {
                'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'percent_used': disk.percent
            }
        },
        'database': db_status,
        'environment': {
            'python_version': os.sys.version.split()[0],
            'platform': os.sys.platform,
            'db_engine': os.environ.get('DB_ENGINE', 'sqlite')
        }
    }


def check_database_connection():
    """Check database connection health"""
    try:
        from backend.db_pool import get_db_connection, DB_ENGINE
        
        with get_db_connection() as (conn, cursor):
            if DB_ENGINE == 'mysql':
                cursor.execute('SELECT 1')
            else:
                cursor.execute('SELECT 1')
            
            result = cursor.fetchone()
            
            return {
                'status': 'connected',
                'engine': DB_ENGINE,
                'response_time_ms': 'N/A'  # Could measure actual query time
            }
    except Exception as e:
        return {
            'status': 'error',
            'engine': os.environ.get('DB_ENGINE', 'unknown'),
            'error': str(e)
        }


def calculate_health_score(cpu, memory, disk, db_status):
    """Calculate overall system health score (0-1)"""
    score = 1.0
    
    # Penalize high resource usage
    if cpu > 80:
        score -= 0.3
    elif cpu > 60:
        score -= 0.1
    
    if memory > 85:
        score -= 0.3
    elif memory > 70:
        score -= 0.1
    
    if disk > 90:
        score -= 0.2
    elif disk > 80:
        score -= 0.1
    
    # Database connection is critical
    if db_status['status'] != 'connected':
        score -= 0.5
    
    return max(0, score)


def format_uptime(seconds):
    """Format uptime in human-readable format"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def get_database_stats():
    """Get database statistics"""
    try:
        from backend.db_pool import get_db_connection, DB_ENGINE
        
        with get_db_connection() as (conn, cursor):
            stats = {
                'engine': DB_ENGINE,
                'tables': {}
            }
            
            # Get table counts
            tables = ['users', 'sellers', 'riders', 'products', 'orders', 'order_items']
            
            for table in tables:
                try:
                    if DB_ENGINE == 'mysql':
                        cursor.execute(f'SELECT COUNT(*) as cnt FROM {table}')
                    else:
                        cursor.execute(f'SELECT COUNT(*) as cnt FROM {table}')
                    
                    result = cursor.fetchone()
                    count = result['cnt'] if isinstance(result, dict) else result[0]
                    stats['tables'][table] = count
                except:
                    stats['tables'][table] = 'N/A'
            
            return stats
    except Exception as e:
        return {
            'error': str(e)
        }


def health_check_endpoint():
    """Flask endpoint for health check"""
    try:
        health = get_system_health()
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


def detailed_status_endpoint():
    """Flask endpoint for detailed system status"""
    try:
        health = get_system_health()
        db_stats = get_database_stats()
        
        return jsonify({
            'health': health,
            'database_stats': db_stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Export functions
__all__ = [
    'get_system_health',
    'health_check_endpoint',
    'detailed_status_endpoint',
    'get_database_stats'
]
