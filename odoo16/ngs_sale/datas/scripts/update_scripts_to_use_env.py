#!/usr/bin/env python3
"""
Script để tự động update các scripts Python để sử dụng env_loader
"""

import os
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
LOGIN_CONFIGS_DIR = SCRIPTS_DIR.parent / 'login_configs'

def update_script(file_path):
    """Update một script để sử dụng env_loader"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check nếu đã có env_loader thì skip
    if 'from env_loader import' in content or 'import env_loader' in content:
        return False, "Already uses env_loader"
    
    # Pattern để tìm phần import và config
    # Tìm pattern: import os ... url = os.getenv("ODOO_URL")
    pattern1 = r'(import\s+os[^\n]*\n)'
    pattern2 = r'(url\s*=\s*os\.getenv\(["\']ODOO_URL["\']\)[^\n]*\n)'
    pattern3 = r'(db\s*=\s*os\.getenv\(["\']ODOO_DB["\']\)[^\n]*\n)'
    pattern4 = r'(username\s*=\s*os\.getenv\(["\']ODOO_USERNAME["\']\)[^\n]*\n)'
    pattern5 = r'(password\s*=\s*os\.getenv\(["\']ODOO_PASSWORD["\']\)[^\n]*\n)'
    
    # Tìm phần connection code
    connection_pattern = r'(common\s*=\s*xmlrpc\.client\.ServerProxy[^\n]*\n.*?uid\s*=\s*common\.authenticate[^\n]*\n)'
    
    # Check xem có phải là script cần update không
    has_odoo_connection = (
        'xmlrpc.client' in content and
        'os.getenv' in content and
        ('ODOO_URL' in content or 'ODOO_DB' in content)
    )
    
    if not has_odoo_connection:
        return False, "Not an Odoo connection script"
    
    # Thêm import env_loader ở đầu file (sau shebang và docstring)
    import_block = """import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False
"""
    
    # Tìm vị trí để insert (sau imports)
    lines = content.split('\n')
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
        elif line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
            break
    
    # Insert import block
    lines.insert(insert_pos, import_block)
    content = '\n'.join(lines)
    
    # Thay thế phần connection
    # Tìm và thay thế phần từ url = ... đến uid = ...
    connection_replacement = """# Get connection với hỗ trợ 3 môi trường
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        sys.exit(1)
else:
    # Fallback: dùng environment variables trực tiếp
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USERNAME")
    password = os.getenv("ODOO_PASSWORD")
    
    if not all([url, db, username, password]):
        print("❌ Missing environment variables. Please:")
        print("   1. Run: source load_env.sh [prod|staging|local]")
        print("   2. Or set: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
        sys.exit(1)
    
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)
"""
    
    # Tìm và replace phần connection cũ
    # Pattern: từ url = os.getenv đến uid = common.authenticate
    old_connection_pattern = r'(url\s*=\s*os\.getenv\([^)]+\)[^\n]*\n.*?uid\s*=\s*common\.authenticate\([^)]+\)[^\n]*\n)'
    
    if re.search(old_connection_pattern, content, re.DOTALL):
        content = re.sub(old_connection_pattern, connection_replacement, content, flags=re.DOTALL)
    else:
        # Nếu không tìm thấy pattern, thử tìm từng phần
        # Tìm phần từ "Config" hoặc "# Config" đến "uid ="
        config_pattern = r'(#\s*Config[^\n]*\n.*?uid\s*=\s*[^\n]+\n)'
        if re.search(config_pattern, content, re.DOTALL):
            content = re.sub(config_pattern, connection_replacement, content, flags=re.DOTALL)
        else:
            return False, "Could not find connection pattern to replace"
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, "Updated successfully"
    
    return False, "No changes needed"

def main():
    """Update tất cả scripts trong thư mục"""
    updated = []
    skipped = []
    errors = []
    
    # Tìm tất cả file .py trong scripts directory
    for py_file in SCRIPTS_DIR.rglob('*.py'):
        # Skip một số files
        if py_file.name in ['__init__.py', 'update_scripts_to_use_env.py', 'SCRIPT_TEMPLATE.py']:
            continue
        
        # Skip nếu là test file với env_loader
        if 'with_env' in py_file.name:
            continue
        
        try:
            success, message = update_script(py_file)
            if success:
                updated.append(str(py_file.relative_to(SCRIPTS_DIR)))
            else:
                skipped.append(f"{py_file.name}: {message}")
        except Exception as e:
            errors.append(f"{py_file.name}: {str(e)}")
    
    # Print results
    print("=" * 60)
    print("SCRIPT UPDATE RESULTS")
    print("=" * 60)
    print(f"\n✅ Updated ({len(updated)}):")
    for f in updated[:10]:  # Show first 10
        print(f"   - {f}")
    if len(updated) > 10:
        print(f"   ... and {len(updated) - 10} more")
    
    if skipped:
        print(f"\n⏭️  Skipped ({len(skipped)}):")
        for s in skipped[:5]:
            print(f"   - {s}")
        if len(skipped) > 5:
            print(f"   ... and {len(skipped) - 5} more")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for e in errors:
            print(f"   - {e}")
    
    print(f"\n📊 Summary: {len(updated)} updated, {len(skipped)} skipped, {len(errors)} errors")

if __name__ == '__main__':
    main()
