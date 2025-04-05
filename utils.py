import json
import logging
from datetime import datetime
from flask import Response

logger = logging.getLogger(__name__)

def json_response(data, status_code=200):
    """
    Create a JSON HTTP response
    
    Args:
        data (dict): Dictionary to serialize to JSON
        status_code (int): HTTP status code
        
    Returns:
        Response: Flask Response object
    """
    response = Response(
        json.dumps(data),
        status=status_code,
        mimetype='application/json'
    )
    return response

class DateTimeEncoder(json.JSONEncoder):
    """JSON Encoder that can handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def format_datetime(dt):
    """Format datetime object for display"""
    if not dt:
        return ""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime(dt_str):
    """Parse datetime string to datetime object"""
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None

def get_pagination_params(request, default_page=1, default_per_page=20):
    """
    Get pagination parameters from request
    
    Args:
        request: Flask request object
        default_page (int): Default page number
        default_per_page (int): Default items per page
        
    Returns:
        tuple: (page, per_page)
    """
    try:
        page = int(request.args.get('page', default_page))
        per_page = int(request.args.get('per_page', default_per_page))
        
        # Ensure valid values
        page = max(1, page)
        per_page = max(1, min(100, per_page))  # Limit per_page between 1 and 100
        
        return page, per_page
    except (ValueError, TypeError):
        return default_page, default_per_page

def generate_pagination_info(page, per_page, total_items):
    """
    Generate pagination information
    
    Args:
        page (int): Current page number
        per_page (int): Items per page
        total_items (int): Total number of items
        
    Returns:
        dict: Pagination information
    """
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division
    
    return {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1
    }
