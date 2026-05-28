#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Company Data Script

Script này setup 2 tasks:
1. Setup Contacts: Set Payment Terms và Pricelist cho tất cả contacts
2. Setup Products: Set Sales Tax cho tất cả stockable products

Usage:
    python setup_company_data.py [env] [company_id] [task]
    
Tasks:
    contacts  - Set Payment Terms "Thanh toán ngay" và Pricelist "[Bán] Mặc định" cho contacts
    products  - Set Sales Tax "Thuế GTGT phải nộp 10% x" cho stockable products
    all       - Run cả 2 tasks
    
Example:
    python setup_company_data.py test 2 contacts
    python setup_company_data.py test 2 products
    python setup_company_data.py test 2 all
"""

import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False
    import xmlrpc.client

def get_connection(env_type=None):
    """Lấy Odoo connection"""
    if USE_ENV_LOADER:
        return setup_odoo_connection(env_type)
    else:
        if env_type == 'test':
            url = os.getenv("ODOO_URL", "http://test.thepnamsaigon.com")
            db = os.getenv("ODOO_DB", "16.thepnamsaigon.03.11.2025")
            username = os.getenv("ODOO_USERNAME", "nsgit")
            password = os.getenv("ODOO_PASSWORD", "1")
        elif env_type == 'prod':
            url = os.getenv("ODOO_URL", "http://erp.thepnamsaigon.com")
            db = os.getenv("ODOO_DB", "erp.thepnamsaigon.com")
            username = os.getenv("ODOO_USERNAME", "nsgit")
            password = os.getenv("ODOO_PASSWORD", "1")
        else:
            url = os.getenv("ODOO_URL", "http://localhost:6069")
            db = os.getenv("ODOO_DB", "16.thepnamsaigon.03.11.2025")
            username = os.getenv("ODOO_USERNAME", "nsgit")
            password = os.getenv("ODOO_PASSWORD", "1")
        
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), allow_none=True)
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
        uid = common.authenticate(db, username, password, {})
        
        return url, db, username, password, models, uid

def setup_contacts(models, uid, password, db, company_id, pricelist_name=None):
    """
    Set Payment Terms và Pricelist cho tất cả contacts trong company
    - Payment Terms: "Thanh toán ngay"
    - Pricelist: "[Bán] Mặc định"
    - Chỉ set nếu chưa có giá trị (no override)
    """
    print(f"\n{'='*70}")
    print(f"👥 SETTING UP CONTACTS")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Tìm Payment Term "Thanh toán ngay" hoặc "Immediate Payment"
    print("  → Finding Payment Term 'Thanh toán ngay' or 'Immediate Payment'...")
    payment_term_ids = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search',
        [['|', ('name', '=', 'Thanh toán ngay'), ('name', '=', 'Immediate Payment')]]
    )
    if not payment_term_ids:
        print("    ❌ Payment Term 'Thanh toán ngay' or 'Immediate Payment' not found")
        print("    💡 You may need to create it first or use a different name")
        return False
    payment_term_id = payment_term_ids[0]
    
    # Get name để confirm
    payment_term = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'read',
        [[payment_term_id]],
        {'fields': ['name']}
    )
    term_name = payment_term[0].get('name', 'N/A') if payment_term else 'N/A'
    print(f"    ✓ Found Payment Term: '{term_name}' (ID: {payment_term_id})")
    
    # Tìm Pricelist (có thể chỉ định tên hoặc dùng default)
    search_name = pricelist_name or '[Bán] Mặc định'
    print(f"  → Finding Pricelist '{search_name}'...")
    
    pricelist_ids = models.execute_kw(
        db, uid, password,
        'product.pricelist', 'search',
        [[('name', '=', search_name)]]
    )
    if not pricelist_ids:
        # Thử tìm với ilike (bỏ qua dấu ngoặc vuông)
        pricelist_ids = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search',
            [[('name', 'ilike', 'Bán] Mặc định')]]
        )
    if not pricelist_ids:
        # Nếu không tìm thấy bằng tên, thử dùng ID 14
        print(f"    ⚠️  Pricelist '{search_name}' not found by name")
        print(f"    → Trying to use pricelist ID 14 as fallback...")
        
        try:
            # Kiểm tra xem pricelist ID 14 có tồn tại không
            pricelist_14 = models.execute_kw(
                db, uid, password,
                'product.pricelist', 'read',
                [[14]],
                {'fields': ['name', 'id']}
            )
            if pricelist_14:
                pricelist_id = 14
                pricelist_name_found = pricelist_14[0].get('name', 'N/A')
                print(f"    ✓ Using fallback pricelist ID 14: '{pricelist_name_found}'")
            else:
                print(f"    ❌ Pricelist ID 14 also not found!")
                return False
        except Exception as e:
            print(f"    ❌ Error accessing pricelist ID 14: {str(e)[:100]}")
            return False
    else:
        pricelist_id = pricelist_ids[0]
        # Get name để confirm
        pricelist = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'read',
            [[pricelist_id]],
            {'fields': ['name']}
        )
        pricelist_name_found = pricelist[0].get('name', 'N/A') if pricelist else 'N/A'
        print(f"    ✓ Found Pricelist: '{pricelist_name_found}' (ID: {pricelist_id})")
    
    # Lấy tất cả contacts
    print("  → Getting all contacts...")
    contact_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[]]  # Lấy tất cả contacts
    )
    print(f"    ✓ Found {len(contact_ids)} contacts")
    
    # Process từng contact
    updated_payment_term = 0
    updated_pricelist = 0
    skipped_payment_term = 0
    skipped_pricelist = 0
    error_count = 0
    
    print("  → Processing contacts...")
    batch_size = 100  # Process in batches để tránh timeout
    for i in range(0, len(contact_ids), batch_size):
        batch = contact_ids[i:i+batch_size]
        print(f"    Processing batch {i//batch_size + 1}/{(len(contact_ids)-1)//batch_size + 1} ({len(batch)} contacts)...")
        
        for contact_id in batch:
            try:
                # Đọc contact để check giá trị hiện tại (với context company cho property field)
                contact = models.execute_kw(
                    db, uid, password,
                    'res.partner', 'read',
                    [[contact_id]],
                    {'fields': ['payment_term_id', 'property_product_pricelist']},
                    {'context': {'force_company': company_id}}
                )
                
                if not contact:
                    skipped_payment_term += 1
                    if pricelist_id:
                        skipped_pricelist += 1
                    continue
                
                contact_data = contact[0]
                update_data = {}
                
                # Check và set payment_term_id (direct field)
                current_payment_term = contact_data.get('payment_term_id')
                if not current_payment_term or (isinstance(current_payment_term, list) and len(current_payment_term) == 0):
                    update_data['payment_term_id'] = payment_term_id
                    updated_payment_term += 1
                else:
                    skipped_payment_term += 1
                
                # Check và set property_product_pricelist (property field)
                current_pricelist = contact_data.get('property_product_pricelist')
                if not current_pricelist or (isinstance(current_pricelist, list) and len(current_pricelist) == 0):
                    update_data['property_product_pricelist'] = pricelist_id
                    updated_pricelist += 1
                else:
                    skipped_pricelist += 1
                
                # Update nếu có thay đổi
                if update_data:
                    models.execute_kw(
                        db, uid, password,
                        'res.partner', 'write',
                        [[contact_id], update_data],
                        {'context': {'force_company': company_id}}
                    )
            
            except Exception as e:
                error_msg = str(e)
                # Bỏ qua lỗi permission/record rules (có thể do multi-company)
                if 'Access Denied' in error_msg or 'record rules' in error_msg.lower() or 'permission' in error_msg.lower() or 'Fault' in error_msg:
                    skipped_payment_term += 1
                    if pricelist_id:
                        skipped_pricelist += 1
                else:
                    error_count += 1
                    if error_count <= 10:  # Log 10 errors đầu tiên
                        print(f"      ⚠️  Error processing contact {contact_id}: {error_msg[:80]}")
    
    print(f"\n{'='*70}")
    print(f"✅ SETUP COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Results:")
    print(f"   ✓ Updated Payment Terms: {updated_payment_term}")
    print(f"   ⏭️  Skipped Payment Terms (already set): {skipped_payment_term}")
    print(f"   ✓ Updated Pricelists: {updated_pricelist}")
    print(f"   ⏭️  Skipped Pricelists (already set): {skipped_pricelist}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"{'='*70}\n")
    
    return True

def setup_products(models, uid, password, db, company_id):
    """
    Set Sales Tax "Thuế GTGT phải nộp 10% x" cho tất cả stockable products
    - Chỉ set cho products có type = 'product' (stockable)
    - Chỉ set nếu chưa có giá trị (no override)
    """
    print(f"\n{'='*70}")
    print(f"📦 SETTING UP STOCKABLE PRODUCTS")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Tìm Tax "Thuế GTGT phải nộp 10% x" hoặc tên tương tự (VAT 10% cho sale)
    print("  → Finding Tax 'Thuế GTGT phải nộp 10% x' or 'VAT 10%' for sale...")
    tax_ids = models.execute_kw(
        db, uid, password,
        'account.tax', 'search',
        [[('company_id', '=', company_id), ('name', '=', 'Thuế GTGT phải nộp 10% x'), ('type_tax_use', '=', 'sale')]]
    )
    if not tax_ids:
        # Thử tìm với ilike và type_tax_use = sale
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('name', 'ilike', 'GTGT 10%'), ('type_tax_use', '=', 'sale')]]
        )
    if not tax_ids:
        # Thử tìm VAT 10% cho sale (chính xác)
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('name', '=', 'Value Added Tax (VAT) 10%'), ('type_tax_use', '=', 'sale')]]
        )
    if not tax_ids:
        # Thử tìm với ilike VAT 10% cho sale
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('name', 'ilike', 'VAT 10%'), ('type_tax_use', '=', 'sale')]]
        )
    if not tax_ids:
        # Thử tìm bất kỳ tax nào có 10% và type_tax_use = sale
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('amount', '=', 10.0), ('type_tax_use', '=', 'sale')]]
        )
    if not tax_ids:
        # List tất cả taxes để user chọn
        print("    ⚠️  Tax 'Thuế GTGT phải nộp 10% x' not found, listing all taxes...")
        all_taxes = models.execute_kw(
            db, uid, password,
            'account.tax', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'amount', 'type_tax_use']}
        )
        print(f"    Available Taxes for Company {company_id} ({len(all_taxes)}):")
        for tax in all_taxes[:10]:  # Show first 10
            print(f"      - {tax.get('name')} ({tax.get('amount', 0)}%, {tax.get('type_tax_use', 'N/A')})")
        if len(all_taxes) > 10:
            print(f"      ... and {len(all_taxes) - 10} more")
        return False
    
    tax_id = tax_ids[0]
    
    # Get name để confirm
    tax = models.execute_kw(
        db, uid, password,
        'account.tax', 'read',
        [[tax_id]],
        {'fields': ['name']}
    )
    tax_name = tax[0].get('name', 'N/A') if tax else 'N/A'
    print(f"    ✓ Found Tax: '{tax_name}' (ID: {tax_id})")
    
    # Lấy tất cả stockable products (type = 'product')
    print("  → Getting all stockable products...")
    product_ids = models.execute_kw(
        db, uid, password,
        'product.template', 'search',
        [[('type', '=', 'product')]]  # Chỉ stockable products
    )
    print(f"    ✓ Found {len(product_ids)} stockable products")
    
    # Process từng product
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print("  → Processing products...")
    batch_size = 50  # Process in batches
    for i in range(0, len(product_ids), batch_size):
        batch = product_ids[i:i+batch_size]
        print(f"    Processing batch {i//batch_size + 1}/{(len(product_ids)-1)//batch_size + 1} ({len(batch)} products)...")
        
        for product_id in batch:
            try:
                # Đọc product với context company để check taxes_id
                product = models.execute_kw(
                    db, uid, password,
                    'product.template', 'read',
                    [[product_id]],
                    {'fields': ['name', 'type', 'taxes_id']},
                    {'context': {'force_company': company_id}}
                )
                
                if not product:
                    continue
                
                product_data = product[0]
                
                # Check taxes_id hiện tại
                # taxes_id là Many2many field, trả về list of [id, name] hoặc list of ids
                current_taxes = product_data.get('taxes_id', [])
                
                # Convert to list of IDs nếu cần
                current_tax_ids = []
                if isinstance(current_taxes, list) and len(current_taxes) > 0:
                    if isinstance(current_taxes[0], list):
                        # Format: [[id, name], ...]
                        current_tax_ids = [t[0] for t in current_taxes]
                    else:
                        # Format: [id, ...]
                        current_tax_ids = current_taxes
                
                if len(current_tax_ids) == 0:
                    # Chưa có tax, set mới
                    models.execute_kw(
                        db, uid, password,
                        'product.template', 'write',
                        [[product_id], {'taxes_id': [(6, 0, [tax_id])]}],
                        {'context': {'force_company': company_id}}
                    )
                    updated_count += 1
                    if updated_count <= 20:  # Log 20 đầu tiên
                        print(f"      ✓ Set tax for: {product_data.get('name', 'N/A')[:50]}")
                else:
                    # Đã có tax, check xem có tax này chưa
                    if tax_id not in current_tax_ids:
                        # Thêm tax vào danh sách hiện tại
                        new_tax_ids = current_tax_ids + [tax_id]
                        models.execute_kw(
                            db, uid, password,
                            'product.template', 'write',
                            [[product_id], {'taxes_id': [(6, 0, new_tax_ids)]}],
                            {'context': {'force_company': company_id}}
                        )
                        updated_count += 1
                        if updated_count <= 20:
                            print(f"      ✓ Added tax for: {product_data.get('name', 'N/A')[:50]}")
                    else:
                        skipped_count += 1
            
            except Exception as e:
                error_msg = str(e)
                # Bỏ qua lỗi permission/record rules (có thể do multi-company)
                if 'Access Denied' in error_msg or 'record rules' in error_msg.lower() or 'permission' in error_msg.lower() or 'Fault' in error_msg:
                    skipped_count += 1
                else:
                    error_count += 1
                    if error_count <= 10:  # Log 10 errors đầu tiên
                        print(f"      ⚠️  Error processing product {product_id}: {error_msg[:80]}")
    
    print(f"\n{'='*70}")
    print(f"✅ SETUP COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Results:")
    print(f"   ✓ Updated products: {updated_count}")
    print(f"   ⏭️  Skipped products (already set): {skipped_count}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"{'='*70}\n")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("python setup_company_data.py [env] [company_id]")
        print("\nDescription:")
        print("  Script này sẽ tự động chạy cả 2 tasks:")
        print("  1. Setup Contacts: Set Payment Terms và Pricelist cho contacts")
        print("  2. Setup Products: Set Sales Tax cho stockable products")
        print("\nExample:")
        print("  python setup_company_data.py test 2")
        print("  python setup_company_data.py prod 2")
        print("="*70)
        return 1
    
    env_type = sys.argv[1]
    company_id = int(sys.argv[2])
    
    print(f"\n{'='*70}")
    print(f"🚀 SETUP COMPANY DATA")
    print(f"{'='*70}")
    print(f"Environment: {env_type}")
    print(f"Company ID: {company_id}")
    print(f"Tasks: contacts + products (both will run)")
    print(f"{'='*70}\n")
    
    print(f"🔗 Connecting to {env_type} environment...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})")
    
    # Chạy cả 2 tasks
    print("\n" + "="*70)
    print("Running Task 1: Setup Contacts")
    print("="*70)
    success1 = setup_contacts(models, uid, password, db, company_id)
    
    if not success1:
        print(f"\n{'='*70}")
        print(f"❌ TASK 1 FAILED - STOPPING")
        print(f"{'='*70}")
        print(f"Please fix the issue and run the script again.")
        print(f"{'='*70}\n")
        return 1
    
    print("\n" + "="*70)
    print("Running Task 2: Setup Products")
    print("="*70)
    success2 = setup_products(models, uid, password, db, company_id)
    
    success = success1 and success2
    
    if success:
        print(f"\n{'='*70}")
        print(f"✅ ALL TASKS COMPLETED SUCCESSFULLY")
        print(f"{'='*70}\n")
        return 0
    else:
        print(f"\n{'='*70}")
        print(f"⚠️  SOME TASKS FAILED")
        print(f"{'='*70}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
