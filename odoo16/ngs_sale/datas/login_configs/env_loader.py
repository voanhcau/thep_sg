#!/usr/bin/env python3
"""
Helper module để load environment variables từ .env file
Hỗ trợ 3 môi trường: prod, staging, local
"""
import os
from pathlib import Path

def load_env_from_file(env_file=None):
    """
    Load environment variables từ file .env
    """
    if env_file is None:
        # Tìm file .env trong thư mục hiện tại hoặc thư mục cha
        current_dir = Path(__file__).parent.parent.parent.parent.parent
        env_file = current_dir / ".env"
        
        # Nếu không tìm thấy, thử thư mục gốc
        if not env_file.exists():
            env_file = Path("/Users/brucenguyen/Source/16/.env")
    
    if not env_file.exists():
        return False
    
    # Load .env file
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Bỏ qua comments và empty lines
            if not line or line.startswith('#'):
                continue
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes nếu có
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                # Set environment variable nếu chưa có
                if key not in os.environ:
                    os.environ[key] = value
    
    return True

def get_env_config(env_type='prod'):
    """
    Lấy config cho môi trường cụ thể
    
    Args:
        env_type: 'prod', 'staging', hoặc 'local'
    
    Returns:
        dict với keys: url, db, username, password
    """
    env_type = env_type.lower()
    
    # Load .env file nếu chưa load
    load_env_from_file()
    
    if env_type == 'prod' or env_type == 'production':
        return {
            'url': os.getenv('ODOO_URL_PROD'),
            'db': os.getenv('ODOO_DB_PROD'),
            'username': os.getenv('ODOO_USERNAME_PROD'),
            'password': os.getenv('ODOO_PASSWORD_PROD'),
        }
    elif env_type == 'staging' or env_type == 'test':
        return {
            'url': os.getenv('ODOO_URL_STAGING'),
            'db': os.getenv('ODOO_DB_STAGING'),
            'username': os.getenv('ODOO_USERNAME_STAGING'),
            'password': os.getenv('ODOO_PASSWORD_STAGING'),
        }
    elif env_type == 'local':
        return {
            'url': os.getenv('ODOO_URL_LOCAL'),
            'db': os.getenv('ODOO_DB_LOCAL'),
            'username': os.getenv('ODOO_USERNAME_LOCAL'),
            'password': os.getenv('ODOO_PASSWORD_LOCAL'),
        }
    else:
        raise ValueError(f"Unknown environment type: {env_type}. Use 'prod', 'staging', or 'local'")

def get_default_env():
    """
    Lấy default environment (từ ODOO_URL, ODOO_DB, etc.)
    """
    load_env_from_file()
    return {
        'url': os.getenv('ODOO_URL'),
        'db': os.getenv('ODOO_DB'),
        'username': os.getenv('ODOO_USERNAME'),
        'password': os.getenv('ODOO_PASSWORD'),
    }

def setup_odoo_connection(env_type=None):
    """
    Setup Odoo connection với environment type cụ thể
    
    Args:
        env_type: 'prod', 'staging', 'local', hoặc None (dùng default)
    
    Returns:
        tuple: (url, db, username, password, models, uid)
    """
    import xmlrpc.client
    
    # Load config
    if env_type:
        config = get_env_config(env_type)
    else:
        config = get_default_env()
    
    url = config['url']
    db = config['db']
    username = config['username']
    password = config['password']
    
    # Validate
    if not all([url, db, username, password]):
        missing = [k for k, v in config.items() if not v]
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    
    # Connect
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        raise ValueError("Authentication failed")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    
    return url, db, username, password, models, uid
