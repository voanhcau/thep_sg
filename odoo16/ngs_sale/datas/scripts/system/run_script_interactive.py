# coding=utf-8
"""
Script tổng quát để chạy các script khác với interactive login
"""
import sys
import os
import importlib.util

def run_script(script_name):
    """Chạy script với interactive login"""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        print("ERROR: Script %s not found!" % script_name)
        return False
    
    try:
        # Import script
        spec = importlib.util.spec_from_file_location("script", script_path)
        script_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script_module)
        
        # Chạy main function nếu có
        if hasattr(script_module, 'main'):
            script_module.main()
        else:
            print("Script %s không có function main()" % script_name)
            return False
            
        return True
        
    except Exception as e:
        print("ERROR running script %s: %s" % (script_name, str(e)))
        return False

def main():
    """Hàm chính"""
    print("==========================================")
    print("INTERACTIVE SCRIPT RUNNER")
    print("==========================================")
    print("Scripts available:")
    print("1. recompute_invoice_status_interactive.py")
    print("2. test_invoice_status_logic.py")
    print("3. fix_missing_invoice_order_id.py")
    print()
    
    choice = input("Chon script (1-3) hoac nhap ten file: ").strip()
    
    if choice == "1":
        script_name = "recompute_invoice_status_interactive.py"
    elif choice == "2":
        script_name = "test_invoice_status_logic.py"
    elif choice == "3":
        script_name = "fix_missing_invoice_order_id.py"
    else:
        script_name = choice
        if not script_name.endswith('.py'):
            script_name += '.py'
    
    print("\nChay script: %s" % script_name)
    print("=" * 50)
    
    if run_script(script_name):
        print("\n✓ Script completed successfully!")
    else:
        print("\n✗ Script failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
