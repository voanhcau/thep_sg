# coding=utf-8
"""
Interactive login script - hỏi và nhập password
"""
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
import getpass
import sys
import os

def get_login_info():
    """Hỏi thông tin đăng nhập từ user"""
    print("==========================================")
    print("ODOO LOGIN CONFIGURATION")
    print("==========================================")
    
    # Ưu tiên đọc từ environment variables
    db = os.getenv("ODOO_DB")
    url = os.getenv("ODOO_URL")
    username = os.getenv("ODOO_USERNAME")
    
    # Nếu không có trong env, hỏi user
    if not db:
        db = input("Database name: ").strip()
    if not url:
        url = input("URL: ").strip()
    if not username:
        username = input("Username: ").strip()
    
    # Hỏi password (ẩn)
    password = getpass.getpass("Password: ")
    
    return db, url, username, password

def connect_to_odoo():
    """Kết nối đến Odoo với thông tin từ user"""
    try:
        db, url, username, password = get_login_info()
        
        print("\nConnecting to Odoo...")
        print("Database:", db)
        print("URL:", url)
        print("Username:", username)
        
        # Tạo connection
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("ERROR: Authentication failed!")
            return None, None, None, None
        
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
        
        print("✓ Connected successfully!")
        print("User ID:", uid)
        
        return db, uid, password, models
        
    except Exception as e:
        print("ERROR: Connection failed!")
        print("Error:", str(e))
        return None, None, None, None

# Global variables để các script khác import
db = None
uid = None
password = None
models = None

def initialize():
    """Khởi tạo connection"""
    global db, uid, password, models
    db, uid, password, models = connect_to_odoo()
    return db is not None

if __name__ == '__main__':
    # Test connection
    if initialize():
        print("\n✓ Login successful!")
        print("You can now import this module in other scripts.")
    else:
        print("\n✗ Login failed!")
        sys.exit(1)
