#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Setup Results

Script này kiểm tra kết quả setup để đảm bảo đúng với mong muốn:
- Contacts: Payment Terms = "Thanh toán ngay", Pricelist = "[Bán] Mặc định (VND)"
- Products: Sales Tax = "Thuế GTGT phải nộp 10%" (cho stockable products)
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

def verify_contacts(models, uid, password, db, company_id):
    """Verify contacts setup"""
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING CONTACTS SETUP")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Tìm Payment Term "Thanh toán ngay" hoặc "Immediate Payment"
    payment_term_ids = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search',
        [['|', ('name', '=', 'Thanh toán ngay'), ('name', '=', 'Immediate Payment')]]
    )
    if not payment_term_ids:
        print("    ❌ Payment Term not found")
        return False
    expected_payment_term_id = payment_term_ids[0]
    
    payment_term = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'read',
        [[expected_payment_term_id]],
        {'fields': ['name']}
    )
    payment_term_name = payment_term[0].get('name', 'N/A') if payment_term else 'N/A'
    print(f"  Expected Payment Term: '{payment_term_name}' (ID: {expected_payment_term_id})")
    
    # Tìm Pricelist "[Bán] Mặc định (VND)"
    pricelist_ids = models.execute_kw(
        db, uid, password,
        'product.pricelist', 'search',
        [[('name', '=', '[Bán] Mặc định (VND)')]]
    )
    expected_pricelist_id = None
    if pricelist_ids:
        expected_pricelist_id = pricelist_ids[0]
        pricelist = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'read',
            [[expected_pricelist_id]],
            {'fields': ['name']}
        )
        pricelist_name = pricelist[0].get('name', 'N/A') if pricelist else 'N/A'
        print(f"  Expected Pricelist: '{pricelist_name}' (ID: {expected_pricelist_id})")
    else:
        print(f"  ⚠️  Pricelist '[Bán] Mặc định (VND)' not found (will skip pricelist check)")
    
    # Lấy sample contacts để verify
    print("\n  → Sampling contacts for verification...")
    contact_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[]],
        {'limit': 20}  # Sample 20 contacts
    )
    
    print(f"  → Found {len(contact_ids)} contact IDs: {contact_ids[:5]}...")
    
    correct_payment_term = 0
    incorrect_payment_term = 0
    missing_payment_term = 0
    
    correct_pricelist = 0
    incorrect_pricelist = 0
    missing_pricelist = 0
    
    print(f"  → Checking {len(contact_ids)} sample contacts...")
    
    checked_count = 0
    for contact_id in contact_ids:
        try:
            contact = models.execute_kw(
                db, uid, password,
                'res.partner', 'read',
                [[contact_id]],
                {'fields': ['name', 'payment_term_id', 'property_product_pricelist']},
                {'context': {'force_company': company_id}}
            )
            
            if not contact or len(contact) == 0:
                if checked_count < 3:
                    print(f"    ⚠️  Contact {contact_id}: No data returned")
                continue
            
            checked_count += 1
            
            contact_data = contact[0]
            contact_name = contact_data.get('name', 'N/A')
            
            # Check payment_term_id
            current_payment_term = contact_data.get('payment_term_id')
            if current_payment_term:
                if isinstance(current_payment_term, list) and len(current_payment_term) > 0:
                    current_payment_term_id = current_payment_term[0]
                    if current_payment_term_id == expected_payment_term_id:
                        correct_payment_term += 1
                    else:
                        incorrect_payment_term += 1
                        if incorrect_payment_term <= 5:
                            print(f"    ⚠️  Contact '{contact_name}' has different payment term (ID: {current_payment_term_id})")
                elif isinstance(current_payment_term, (int, float)):
                    if current_payment_term == expected_payment_term_id:
                        correct_payment_term += 1
                    else:
                        incorrect_payment_term += 1
            else:
                missing_payment_term += 1
                if missing_payment_term <= 5:
                    print(f"    ⚠️  Contact '{contact_name}' missing payment term")
            
            # Check pricelist
            if expected_pricelist_id:
                current_pricelist = contact_data.get('property_product_pricelist')
                if current_pricelist:
                    if isinstance(current_pricelist, list) and len(current_pricelist) > 0:
                        current_pricelist_id = current_pricelist[0]
                        if current_pricelist_id == expected_pricelist_id:
                            correct_pricelist += 1
                        else:
                            incorrect_pricelist += 1
                    elif isinstance(current_pricelist, (int, float)):
                        if current_pricelist == expected_pricelist_id:
                            correct_pricelist += 1
                        else:
                            incorrect_pricelist += 1
                else:
                    missing_pricelist += 1
        
        except Exception as e:
            error_msg = str(e)
            if 'Access Denied' in error_msg or 'record rules' in error_msg.lower():
                # Skip permission errors
                continue
            if checked_count < 5:  # Log first 5 errors
                print(f"    ⚠️  Error reading contact {contact_id}: {error_msg[:100]}")
            continue
    
    print(f"  → Successfully checked {checked_count}/{len(contact_ids)} contacts")
    
    print(f"\n  📊 Payment Terms Results:")
    print(f"     ✓ Correct: {correct_payment_term}/{checked_count}")
    print(f"     ⚠️  Incorrect: {incorrect_payment_term}/{checked_count}")
    print(f"     ❌ Missing: {missing_payment_term}/{checked_count}")
    
    if expected_pricelist_id:
        print(f"\n  📊 Pricelist Results:")
        print(f"     ✓ Correct: {correct_pricelist}/{checked_count}")
        print(f"     ⚠️  Incorrect: {incorrect_pricelist}/{checked_count}")
        print(f"     ❌ Missing: {missing_pricelist}/{checked_count}")
    
    return True

def verify_products(models, uid, password, db, company_id):
    """Verify products setup"""
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING PRODUCTS SETUP")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Tìm Tax "Thuế GTGT phải nộp 10% x" hoặc tương tự
    tax_ids = models.execute_kw(
        db, uid, password,
        'account.tax', 'search',
        [[('company_id', '=', company_id), ('name', '=', 'Thuế GTGT phải nộp 10% x'), ('type_tax_use', '=', 'sale')]]
    )
    if not tax_ids:
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('name', '=', 'Value Added Tax (VAT) 10%'), ('type_tax_use', '=', 'sale')]]
        )
    if not tax_ids:
        tax_ids = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('amount', '=', 10.0), ('type_tax_use', '=', 'sale')]]
        )
    
    if not tax_ids:
        print("    ❌ Sales Tax 10% not found")
        return False
    
    expected_tax_id = tax_ids[0]
    tax = models.execute_kw(
        db, uid, password,
        'account.tax', 'read',
        [[expected_tax_id]],
        {'fields': ['name']}
    )
    tax_name = tax[0].get('name', 'N/A') if tax else 'N/A'
    print(f"  Expected Sales Tax: '{tax_name}' (ID: {expected_tax_id})")
    
    # Lấy sample stockable products để verify
    print("\n  → Sampling stockable products for verification...")
    product_ids = models.execute_kw(
        db, uid, password,
        'product.template', 'search',
        [[('type', '=', 'product')]],
        {'limit': 20}  # Sample 20 products
    )
    
    print(f"  → Found {len(product_ids)} product IDs: {product_ids[:5]}...")
    
    correct_tax = 0
    incorrect_tax = 0
    missing_tax = 0
    
    print(f"  → Checking {len(product_ids)} sample products...")
    
    checked_count = 0
    for product_id in product_ids:
        try:
            product = models.execute_kw(
                db, uid, password,
                'product.template', 'read',
                [[product_id]],
                {'fields': ['name', 'type', 'taxes_id']},
                {'context': {'force_company': company_id}}
            )
            
            if not product or len(product) == 0:
                if checked_count < 3:
                    print(f"    ⚠️  Product {product_id}: No data returned")
                continue
            
            checked_count += 1
            
            product_data = product[0]
            product_name = product_data.get('name', 'N/A')
            
            # Check taxes_id
            current_taxes = product_data.get('taxes_id', [])
            current_tax_ids = []
            if isinstance(current_taxes, list) and len(current_taxes) > 0:
                if isinstance(current_taxes[0], list):
                    current_tax_ids = [t[0] for t in current_taxes]
                else:
                    current_tax_ids = current_taxes
            
            if expected_tax_id in current_tax_ids:
                correct_tax += 1
            elif len(current_tax_ids) > 0:
                incorrect_tax += 1
                if incorrect_tax <= 5:
                    print(f"    ⚠️  Product '{product_name[:50]}' has different tax (IDs: {current_tax_ids})")
            else:
                missing_tax += 1
                if missing_tax <= 5:
                    print(f"    ⚠️  Product '{product_name[:50]}' missing sales tax")
        
        except Exception as e:
            error_msg = str(e)
            if 'Access Denied' in error_msg or 'record rules' in error_msg.lower():
                # Skip permission errors
                continue
            if checked_count < 5:  # Log first 5 errors
                print(f"    ⚠️  Error reading product {product_id}: {error_msg[:100]}")
            continue
    
    print(f"  → Successfully checked {checked_count}/{len(product_ids)} products")
    
    print(f"\n  📊 Sales Tax Results:")
    print(f"     ✓ Correct: {correct_tax}/{checked_count}")
    print(f"     ⚠️  Incorrect: {incorrect_tax}/{checked_count}")
    print(f"     ❌ Missing: {missing_tax}/{checked_count}")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("python verify_setup.py [env] [company_id]")
        print("\nExample:")
        print("  python verify_setup.py test 2")
        print("="*70)
        return 1
    
    env_type = sys.argv[1]
    company_id = int(sys.argv[2])
    
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING SETUP RESULTS")
    print(f"{'='*70}")
    print(f"Environment: {env_type}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    print(f"🔗 Connecting to {env_type} environment...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})")
    
    verify_contacts(models, uid, password, db, company_id)
    verify_products(models, uid, password, db, company_id)
    
    print(f"\n{'='*70}")
    print(f"✅ VERIFICATION COMPLETED")
    print(f"{'='*70}\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
