#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Production Results

Script này kiểm tra kết quả trên production xem đã đạt được như mong đợi chưa:
- Contacts: Payment Terms = "Thanh toán ngay", Pricelist = "[Bán] Mặc định (VND)"
- Products: Sales Tax = "Thuế GTGT phải nộp 10%"
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
        if env_type == 'prod':
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
    print(f"🔍 VERIFYING CONTACTS - PRODUCTION")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Expected values
    print("📋 Expected Values:")
    print("  - Payment Terms: 'Thanh toán ngay' or 'Immediate Payment'")
    print("  - Pricelist: '[Bán] Mặc định (VND)' or ID 14")
    print()
    
    # Tìm Payment Term
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
    print(f"  ✓ Expected Payment Term: '{payment_term_name}' (ID: {expected_payment_term_id})")
    
    # Tìm Pricelist
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
        print(f"  ✓ Expected Pricelist: '{pricelist_name}' (ID: {expected_pricelist_id})")
    else:
        # Fallback to ID 14
        try:
            pricelist_14 = models.execute_kw(
                db, uid, password,
                'product.pricelist', 'read',
                [[14]],
                {'fields': ['name']}
            )
            if pricelist_14:
                expected_pricelist_id = 14
                pricelist_name = pricelist_14[0].get('name', 'N/A')
                print(f"  ⚠️  Pricelist '[Bán] Mặc định (VND)' not found, using fallback ID 14: '{pricelist_name}'")
        except:
            print(f"  ❌ Pricelist '[Bán] Mặc định (VND)' not found and ID 14 also not found")
            return False
    
    # Sample contacts
    print("\n  → Sampling contacts for verification...")
    contact_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[]],
        {'limit': 30}  # Sample 30 contacts
    )
    
    print(f"  → Checking {len(contact_ids)} sample contacts...")
    
    correct_payment_term = 0
    incorrect_payment_term = 0
    missing_payment_term = 0
    
    correct_pricelist = 0
    incorrect_pricelist = 0
    missing_pricelist = 0
    
    checked_count = 0
    
    for contact_id in contact_ids:
        try:
            # Thử đọc với sudo context hoặc không có context
            contact = models.execute_kw(
                db, uid, password,
                'res.partner', 'read',
                [[contact_id]],
                {'fields': ['name', 'payment_term_id', 'property_product_pricelist']}
            )
            
            if not contact or len(contact) == 0:
                # Thử với context company
                try:
                    contact = models.execute_kw(
                        db, uid, password,
                        'res.partner', 'read',
                        [[contact_id]],
                        {'fields': ['name', 'payment_term_id', 'property_product_pricelist']},
                        {'context': {'force_company': company_id}}
                    )
                except:
                    continue
                if not contact or len(contact) == 0:
                    continue
            
            checked_count += 1
            contact_data = contact[0]
            contact_name = contact_data.get('name', 'N/A')
            
            # Check payment_term_id
            current_payment_term = contact_data.get('payment_term_id')
            if current_payment_term:
                if isinstance(current_payment_term, list) and len(current_payment_term) > 0:
                    current_payment_term_id = current_payment_term[0]
                elif isinstance(current_payment_term, (int, float)):
                    current_payment_term_id = int(current_payment_term)
                else:
                    current_payment_term_id = None
                
                if current_payment_term_id == expected_payment_term_id:
                    correct_payment_term += 1
                else:
                    incorrect_payment_term += 1
                    if incorrect_payment_term <= 3:
                        print(f"    ⚠️  Contact '{contact_name[:40]}' has different payment term (ID: {current_payment_term_id})")
            else:
                missing_payment_term += 1
                if missing_payment_term <= 3:
                    print(f"    ⚠️  Contact '{contact_name[:40]}' missing payment term")
            
            # Check pricelist
            if expected_pricelist_id:
                current_pricelist = contact_data.get('property_product_pricelist')
                if current_pricelist:
                    if isinstance(current_pricelist, list) and len(current_pricelist) > 0:
                        current_pricelist_id = current_pricelist[0]
                    elif isinstance(current_pricelist, (int, float)):
                        current_pricelist_id = int(current_pricelist)
                    else:
                        current_pricelist_id = None
                    
                    if current_pricelist_id == expected_pricelist_id:
                        correct_pricelist += 1
                    else:
                        incorrect_pricelist += 1
                        if incorrect_pricelist <= 3:
                            print(f"    ⚠️  Contact '{contact_name[:40]}' has different pricelist (ID: {current_pricelist_id})")
                else:
                    missing_pricelist += 1
                    if missing_pricelist <= 3:
                        print(f"    ⚠️  Contact '{contact_name[:40]}' missing pricelist")
        
        except Exception as e:
            continue
    
    print(f"\n  → Successfully checked {checked_count}/{len(contact_ids)} contacts")
    
    print(f"\n  📊 Payment Terms Results:")
    print(f"     ✓ Correct: {correct_payment_term}/{checked_count} ({correct_payment_term*100//checked_count if checked_count > 0 else 0}%)")
    print(f"     ⚠️  Incorrect: {incorrect_payment_term}/{checked_count}")
    print(f"     ❌ Missing: {missing_payment_term}/{checked_count}")
    
    if expected_pricelist_id:
        print(f"\n  📊 Pricelist Results:")
        print(f"     ✓ Correct: {correct_pricelist}/{checked_count} ({correct_pricelist*100//checked_count if checked_count > 0 else 0}%)")
        print(f"     ⚠️  Incorrect: {incorrect_pricelist}/{checked_count}")
        print(f"     ❌ Missing: {missing_pricelist}/{checked_count}")
    
    # Overall assessment
    payment_term_rate = (correct_payment_term * 100) // checked_count if checked_count > 0 else 0
    pricelist_rate = (correct_pricelist * 100) // checked_count if checked_count > 0 else 0
    
    print(f"\n  ✅ Overall Assessment:")
    if payment_term_rate >= 95:
        print(f"     ✅ Payment Terms: {payment_term_rate}% correct - PASS")
    else:
        print(f"     ⚠️  Payment Terms: {payment_term_rate}% correct - NEEDS ATTENTION")
    
    if pricelist_rate >= 95:
        print(f"     ✅ Pricelist: {pricelist_rate}% correct - PASS")
    else:
        print(f"     ⚠️  Pricelist: {pricelist_rate}% correct - NEEDS ATTENTION")
    
    return payment_term_rate >= 95 and pricelist_rate >= 95

def verify_products(models, uid, password, db, company_id):
    """Verify products setup"""
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING PRODUCTS - PRODUCTION")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Expected values
    print("📋 Expected Values:")
    print("  - Sales Tax: 'Thuế GTGT phải nộp 10%' or 'Value Added Tax (VAT) 10%'")
    print()
    
    # Tìm Tax
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
    print(f"  ✓ Expected Sales Tax: '{tax_name}' (ID: {expected_tax_id})")
    
    # Sample products
    print("\n  → Sampling stockable products for verification...")
    product_ids = models.execute_kw(
        db, uid, password,
        'product.template', 'search',
        [[('type', '=', 'product')]],
        {'limit': 30}  # Sample 30 products
    )
    
    print(f"  → Checking {len(product_ids)} sample products...")
    
    correct_tax = 0
    incorrect_tax = 0
    missing_tax = 0
    checked_count = 0
    
    for product_id in product_ids:
        try:
            # Thử đọc không có context trước
            product = models.execute_kw(
                db, uid, password,
                'product.template', 'read',
                [[product_id]],
                {'fields': ['name', 'type', 'taxes_id']}
            )
            
            if not product or len(product) == 0:
                # Thử với context company
                try:
                    product = models.execute_kw(
                        db, uid, password,
                        'product.template', 'read',
                        [[product_id]],
                        {'fields': ['name', 'type', 'taxes_id']},
                        {'context': {'force_company': company_id}}
                    )
                except:
                    continue
                if not product or len(product) == 0:
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
                if incorrect_tax <= 3:
                    print(f"    ⚠️  Product '{product_name[:50]}' has different tax (IDs: {current_tax_ids})")
            else:
                missing_tax += 1
                if missing_tax <= 3:
                    print(f"    ⚠️  Product '{product_name[:50]}' missing sales tax")
        
        except Exception as e:
            continue
    
    print(f"  → Successfully checked {checked_count}/{len(product_ids)} products")
    
    print(f"\n  📊 Sales Tax Results:")
    print(f"     ✓ Correct: {correct_tax}/{checked_count} ({correct_tax*100//checked_count if checked_count > 0 else 0}%)")
    print(f"     ⚠️  Incorrect: {incorrect_tax}/{checked_count}")
    print(f"     ❌ Missing: {missing_tax}/{checked_count}")
    
    # Overall assessment
    tax_rate = (correct_tax * 100) // checked_count if checked_count > 0 else 0
    
    print(f"\n  ✅ Overall Assessment:")
    if tax_rate >= 95:
        print(f"     ✅ Sales Tax: {tax_rate}% correct - PASS")
    else:
        print(f"     ⚠️  Sales Tax: {tax_rate}% correct - NEEDS ATTENTION")
    
    return tax_rate >= 95

def main():
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING PRODUCTION RESULTS")
    print(f"{'='*70}")
    print(f"Environment: Production")
    print(f"Company ID: 2")
    print(f"{'='*70}\n")
    
    print(f"🔗 Connecting to production environment...")
    url, db, username, password, models, uid = get_connection('prod')
    print(f"✅ Connected to {url} (DB: {db})")
    
    company_id = 2
    
    result1 = verify_contacts(models, uid, password, db, company_id)
    result2 = verify_products(models, uid, password, db, company_id)
    
    print(f"\n{'='*70}")
    print(f"📊 FINAL VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    if result1 and result2:
        print(f"✅ ALL VERIFICATIONS PASSED")
        print(f"   - Contacts: Payment Terms & Pricelist ✅")
        print(f"   - Products: Sales Tax ✅")
    else:
        print(f"⚠️  SOME VERIFICATIONS NEED ATTENTION")
        if not result1:
            print(f"   - Contacts: ⚠️  Needs review")
        if not result2:
            print(f"   - Products: ⚠️  Needs review")
    
    print(f"{'='*70}\n")
    
    return 0 if (result1 and result2) else 1

if __name__ == '__main__':
    sys.exit(main())
