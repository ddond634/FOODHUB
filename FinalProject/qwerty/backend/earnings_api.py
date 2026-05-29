"""
Earnings API for Seller Dashboard
Handles all earnings-related endpoints including:
- Earnings summary and metrics
- Transaction history
- Commission breakdown
- Income reports
- Payout management
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from backend.auth import role_required, get_token_from_request, verify_token
from backend.api_utils import success_response, error_response, format_row
import os

earnings_bp = Blueprint('earnings', __name__, url_prefix='/api/sellers')

def get_platform_commission_rate():
    """
    Get platform commission rate as decimal (e.g., 0.10 for 10%)
    Returns float between 0 and 1
    """
    try:
        from backend.server import get_platform_commission_rate as get_commission
        return get_commission()
    except Exception:
        return 0.10  # Default 10% if can't get from settings

# Get DB_ENGINE from environment
DB_ENGINE = os.environ.get('DB_ENGINE','mysql').lower()

def get_db_connection():
    """Get database connection using the same method as server.py"""
    from backend.server import get_db
    return get_db()

@earnings_bp.route('/earnings/summary', methods=['GET'])
@role_required('seller')
def get_earnings_summary():
    """
    Get comprehensive earnings summary for seller - supports store_id filtering
    Includes: total earnings, gross revenue, commission, pending payout, paid out, completed orders
    """
    try:
        seller_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'all')  # all, daily, weekly, monthly, yearly
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            base_params = [seller_id, store_id]
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            base_params = [seller_id]
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            base_params = [seller_id]
        
        # Build date filter
        date_filter = ""
        params = base_params.copy()
        
        if start_date and end_date:
            if DB_ENGINE == 'mysql':
                date_filter = " AND o.created_at BETWEEN %s AND %s"
            else:
                date_filter = " AND o.created_at BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        elif period != 'all':
            if period == 'daily':
                days = 1
            elif period == 'weekly':
                days = 7
            elif period == 'monthly':
                days = 30
            elif period == 'yearly':
                days = 365
            else:
                days = 30
            
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            if DB_ENGINE == 'mysql':
                date_filter = " AND o.created_at >= %s"
            else:
                date_filter = " AND o.created_at >= ?"
            params.append(start)
        
        # Get gross revenue and order count
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    COALESCE(SUM(oi.price * oi.quantity), 0) as gross_revenue,
                    COUNT(DISTINCT o.id) as completed_orders
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                {date_filter}
            ''', tuple(params))
        else:
            cursor.execute(f'''
                SELECT 
                    COALESCE(SUM(oi.price * oi.quantity), 0) as gross_revenue,
                    COUNT(DISTINCT o.id) as completed_orders
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                {date_filter}
            ''', tuple(params))
        
        result = cursor.fetchone()
        result_dict = format_row(result) if result else {}
        
        gross_revenue = float(result_dict.get('gross_revenue', 0))
        completed_orders = int(result_dict.get('completed_orders', 0))
        
        # Calculate commission and net earnings
        commission_rate = get_platform_commission_rate()
        platform_commission = gross_revenue * commission_rate
        total_earnings = gross_revenue - platform_commission
        
        # Get pending payout (orders that are completed/shipped but not paid out yet)
        # For now, we'll consider all completed orders as pending payout
        # In production, you'd have a payouts table to track this
        pending_payout = total_earnings  # Simplified - all earnings are pending
        paid_out = 0.00  # Would come from payouts table
        
        # Get comparison with previous period
        if period != 'all':
            if period == 'daily':
                prev_start = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
                prev_end = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            elif period == 'weekly':
                prev_start = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
                prev_end = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif period == 'monthly':
                prev_start = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
                prev_end = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            else:
                prev_start = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
                prev_end = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            if DB_ENGINE == 'mysql':
                prev_date_filter = " AND o.created_at BETWEEN %s AND %s"
            else:
                prev_date_filter = " AND o.created_at BETWEEN ? AND ?"
            
            # Build prev_params with store_id filter
            if store_id and store_id_column_exists:
                prev_base_params = [seller_id, store_id]
            elif store_id_column_exists:
                prev_base_params = [seller_id]
            else:
                prev_base_params = [seller_id]
            
            # Always include both prev_start and prev_end since prev_date_filter uses BETWEEN
            prev_params = prev_base_params + [prev_start, prev_end]
            
            if DB_ENGINE == 'mysql':
                cursor.execute(f'''
                    SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as prev_revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN products p ON oi.product_id = p.id
                    WHERE {product_filter}
                    AND o.status IN ('completed', 'shipped')
                    {prev_date_filter}
                ''', tuple(prev_params))
            else:
                cursor.execute(f'''
                    SELECT COALESCE(SUM(oi.price * oi.quantity), 0) as prev_revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    JOIN products p ON oi.product_id = p.id
                    WHERE {product_filter}
                    AND o.status IN ('completed', 'shipped')
                    {prev_date_filter}
                ''', tuple(prev_params))
            
            prev_result = cursor.fetchone()
            prev_result_dict = format_row(prev_result) if prev_result else {}
            prev_revenue = float(prev_result_dict.get('prev_revenue', 0))
            
            commission_rate = get_platform_commission_rate()
            prev_earnings = prev_revenue - (prev_revenue * commission_rate)
            
            if prev_earnings > 0:
                earnings_change = ((total_earnings - prev_earnings) / prev_earnings) * 100
            else:
                earnings_change = 100.0 if total_earnings > 0 else 0.0
        else:
            earnings_change = 0.0
        
        conn.close()
        
        return success_response({
            'total_earnings': round(total_earnings, 2),
            'gross_revenue': round(gross_revenue, 2),
            'platform_commission': round(platform_commission, 2),
            'commission_rate': get_platform_commission_rate() * 100,
            'pending_payout': round(pending_payout, 2),
            'paid_out': round(paid_out, 2),
            'completed_orders': completed_orders,
            'earnings_change_percent': round(earnings_change, 2),
            'period': period
        })
        
    except Exception as e:
        import traceback
        print(f"Error in get_earnings_summary: {str(e)}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return error_response(f"Failed to fetch earnings summary: {str(e)}", 500)


@earnings_bp.route('/earnings/transactions', methods=['GET'])
@role_required('seller')
def get_transaction_history():
    """
    Get detailed transaction history with commission breakdown - supports store_id filtering
    """
    try:
        seller_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        # Filters
        status = request.args.get('status')  # paid, pending, refunded
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        order_id = request.args.get('order_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            base_params = [seller_id, store_id]
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            base_params = [seller_id]
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            base_params = [seller_id]
        
        # Build filters
        filters = []
        params = base_params.copy()
        
        if status:
            if status == 'paid':
                filters.append("o.status = 'completed'")
            elif status == 'pending':
                filters.append("o.status IN ('shipped', 'processing')")
            elif status == 'refunded':
                filters.append("o.status = 'cancelled'")
        else:
            filters.append("o.status IN ('completed', 'shipped', 'processing', 'cancelled')")
        
        if start_date and end_date:
            if DB_ENGINE == 'mysql':
                filters.append("o.created_at BETWEEN %s AND %s")
            else:
                filters.append("o.created_at BETWEEN ? AND ?")
            params.extend([start_date, end_date])
        
        if order_id:
            if DB_ENGINE == 'mysql':
                filters.append("o.id = %s")
            else:
                filters.append("o.id = ?")
            params.append(order_id)
        
        where_clause = " AND ".join(filters)
        
        # Get transactions
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    o.id as order_id,
                    o.created_at,
                    o.status,
                    oi.product_id,
                    p.title as product_name,
                    oi.quantity,
                    oi.price,
                    (oi.price * oi.quantity) as gross_amount,
                    u.first_name,
                    u.last_name,
                    u.email
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                JOIN users u ON o.customer_id = u.id
                WHERE {product_filter} AND {where_clause}
                ORDER BY o.created_at DESC
                LIMIT %s OFFSET %s
            ''', tuple(params + [per_page, offset]))
        else:
            cursor.execute(f'''
                SELECT 
                    o.id as order_id,
                    o.created_at,
                    o.status,
                    oi.product_id,
                    p.title as product_name,
                    oi.quantity,
                    oi.price,
                    (oi.price * oi.quantity) as gross_amount,
                    u.first_name,
                    u.last_name,
                    u.email
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                JOIN users u ON o.customer_id = u.id
                WHERE {product_filter} AND {where_clause}
                ORDER BY o.created_at DESC
                LIMIT ? OFFSET ?
            ''', tuple(params + [per_page, offset]))
        
        rows = cursor.fetchall()
        
        transactions = []
        for row in rows:
            row_dict = format_row(row)
            
            order_id = row_dict.get('order_id')
            created_at = row_dict.get('created_at')
            order_status = row_dict.get('status')
            product_name = row_dict.get('product_name')
            quantity = row_dict.get('quantity')
            price = float(row_dict.get('price', 0))
            gross_amount = float(row_dict.get('gross_amount', 0))
            first_name = row_dict.get('first_name', '')
            last_name = row_dict.get('last_name', '')
            customer_name = f"{first_name} {last_name}".strip() or 'Unknown Customer'
            
            # Convert created_at to string if it's a datetime object
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                created_at_date = created_at.strftime('%Y-%m-%d')
            else:
                created_at_str = str(created_at) if created_at else ''
                created_at_date = created_at_str[:10] if len(created_at_str) >= 10 else ''
            
            commission_rate = get_platform_commission_rate()
            commission = gross_amount * commission_rate
            net_earnings = gross_amount - commission
            
            # Map order status to transaction status
            if order_status == 'completed':
                trans_status = 'paid'
            elif order_status in ['shipped', 'processing']:
                trans_status = 'pending'
            elif order_status == 'cancelled':
                trans_status = 'refunded'
            else:
                trans_status = 'pending'
            
            transactions.append({
                'transaction_id': f"TXN-{created_at_date.replace('-', '')}-{order_id}" if created_at_date else f"TXN-{order_id}",
                'order_id': order_id,
                'date': created_at_str,
                'product_name': product_name,
                'quantity': quantity,
                'price': round(price, 2),
                'gross_amount': round(gross_amount, 2),
                'commission': round(commission, 2),
                'commission_rate': get_platform_commission_rate() * 100,
                'net_earnings': round(net_earnings, 2),
                'status': trans_status,
                'customer_name': customer_name
            })
        
        # Get total count for pagination
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT COUNT(*) as total FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND {where_clause}
            ''', tuple(params))
            count_row = cursor.fetchone()
            count_dict = format_row(count_row)
            total_count = count_dict.get('total', 0) if isinstance(count_dict, dict) else (count_row[0] if isinstance(count_row, (tuple, list)) else 0)
        else:
            cursor.execute(f'''
                SELECT COUNT(*) as total FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter} AND {where_clause}
            ''', tuple(params))
            count_row = cursor.fetchone()
            count_dict = format_row(count_row)
            total_count = count_dict.get('total', 0) if isinstance(count_dict, dict) else (count_row[0] if isinstance(count_row, (tuple, list)) else 0)
        
        conn.close()
        
        return success_response({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        print(f"Error in get_transaction_history: {str(e)}")
        return error_response(f"Failed to fetch transaction history: {str(e)}", 500)


@earnings_bp.route('/earnings/income-report', methods=['GET'])
@role_required('seller')
def get_income_report():
    """
    Get income report data for charts (daily/weekly/monthly breakdown) - supports store_id filtering
    """
    try:
        seller_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly
        days = int(request.args.get('days', 30))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            product_params = (seller_id, store_id, start_date)
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            product_params = (seller_id, start_date)
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            product_params = (seller_id, start_date)
        
        # Group by date
        if DB_ENGINE == 'mysql':
            date_format = "DATE_FORMAT(o.created_at, '%%Y-%%m-%%d')"
            cursor.execute(f'''
                SELECT 
                    {date_format} as date,
                    COALESCE(SUM(oi.price * oi.quantity), 0) as gross_revenue,
                    COUNT(DISTINCT o.id) as orders
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                AND o.created_at >= %s
                GROUP BY {date_format}
                ORDER BY date ASC
            ''', product_params)
        else:
            cursor.execute(f'''
                SELECT 
                    DATE(o.created_at) as date,
                    COALESCE(SUM(oi.price * oi.quantity), 0) as gross_revenue,
                    COUNT(DISTINCT o.id) as orders
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                AND o.created_at >= ?
                GROUP BY DATE(o.created_at)
                ORDER BY date ASC
            ''', product_params)
        
        rows = cursor.fetchall()
        
        report_data = []
        for row in rows:
            row_dict = format_row(row)
            
            # Handle both dict and tuple/list formats
            if isinstance(row_dict, dict) and 'row' not in row_dict:
                date = row_dict.get('date', '')
                gross_revenue = float(row_dict.get('gross_revenue', 0))
                orders = int(row_dict.get('orders', 0))
            elif isinstance(row, (tuple, list)):
                date = str(row[0]) if len(row) > 0 else ''
                gross_revenue = float(row[1]) if len(row) > 1 else 0.0
                orders = int(row[2]) if len(row) > 2 else 0
            else:
                # Fallback
                date = ''
                gross_revenue = 0.0
                orders = 0
            
            commission_rate = get_platform_commission_rate()
            commission = gross_revenue * commission_rate
            net_earnings = gross_revenue - commission
            
            report_data.append({
                'date': date,
                'gross_revenue': round(gross_revenue, 2),
                'commission': round(commission, 2),
                'net_earnings': round(net_earnings, 2),
                'orders': orders
            })
        
        conn.close()
        
        return success_response({
            'report': report_data,
            'period': period,
            'days': days,
            'commission_rate': get_platform_commission_rate() * 100
        })
        
    except Exception as e:
        print(f"Error in get_income_report: {str(e)}")
        return error_response(f"Failed to generate income report: {str(e)}", 500)


@earnings_bp.route('/earnings/commission-breakdown', methods=['GET'])
@role_required('seller')
def get_commission_breakdown():
    """
    Get detailed commission breakdown by order - supports store_id filtering
    """
    try:
        seller_id = g.user_id
        store_id = request.args.get('store_id', type=int)
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if store_id column exists
        store_id_column_exists = False
        try:
            if DB_ENGINE == 'mysql':
                cursor.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
                store_id_column_exists = cursor.fetchone() is not None
            else:
                cursor.execute("PRAGMA table_info(products)")
                columns = cursor.fetchall()
                store_id_column_exists = any(col[1] == 'store_id' for col in columns)
        except Exception:
            pass
        
        # Build product filter
        if store_id and store_id_column_exists:
            product_filter = 'p.seller_id = %s AND p.store_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND p.store_id = ?'
            base_params = [seller_id, store_id]
        elif store_id_column_exists:
            product_filter = 'p.seller_id = %s AND (p.store_id IS NULL OR p.store_id = 0)' if DB_ENGINE == 'mysql' else 'p.seller_id = ? AND (p.store_id IS NULL OR p.store_id = 0)'
            base_params = [seller_id]
        else:
            product_filter = 'p.seller_id = %s' if DB_ENGINE == 'mysql' else 'p.seller_id = ?'
            base_params = [seller_id]
        
        params = base_params.copy()
        date_filter = ""
        
        if start_date and end_date:
            if DB_ENGINE == 'mysql':
                date_filter = " AND o.created_at BETWEEN %s AND %s"
            else:
                date_filter = " AND o.created_at BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        
        if DB_ENGINE == 'mysql':
            cursor.execute(f'''
                SELECT 
                    o.id as order_id,
                    o.created_at,
                    COALESCE(SUM(oi.price * oi.quantity), 0) as order_value
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                {date_filter}
                GROUP BY o.id, o.created_at
                ORDER BY o.created_at DESC
            ''', tuple(params))
        else:
            cursor.execute(f'''
                SELECT 
                    o.id as order_id,
                    o.created_at,
                    COALESCE(SUM(oi.price * oi.quantity), 0) as order_value
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE {product_filter}
                AND o.status IN ('completed', 'shipped')
                {date_filter}
                GROUP BY o.id, o.created_at
                ORDER BY o.created_at DESC
            ''', tuple(params))
        
        rows = cursor.fetchall()
        
        breakdown = []
        for row in rows:
            row_dict = format_row(row)
            
            # Handle both dict and tuple/list formats
            if isinstance(row_dict, dict) and 'row' not in row_dict:
                order_id = row_dict.get('order_id')
                date = row_dict.get('created_at', '')
                order_value = float(row_dict.get('order_value', 0))
            elif isinstance(row, (tuple, list)):
                order_id = row[0] if len(row) > 0 else None
                date = str(row[1]) if len(row) > 1 else ''
                order_value = float(row[2]) if len(row) > 2 else 0.0
            else:
                order_id = None
                date = ''
                order_value = 0.0
            
            commission_rate = get_platform_commission_rate()
            commission = order_value * commission_rate
            
            breakdown.append({
                'order_id': order_id,
                'order_ref': f"#ORD-{order_id}" if order_id else 'N/A',
                'date': date,
                'order_value': round(order_value, 2),
                'commission': round(commission, 2),
                'commission_rate': commission_rate * 100
            })
        
        conn.close()
        
        commission_rate_pct = get_platform_commission_rate() * 100
        return success_response({
            'breakdown': breakdown,
            'commission_rate': commission_rate_pct
        })
        
    except Exception as e:
        print(f"Error in get_commission_breakdown: {str(e)}")
        return error_response(f"Failed to fetch commission breakdown: {str(e)}", 500)
