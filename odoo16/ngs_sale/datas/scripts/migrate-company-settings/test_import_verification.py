#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test và Verify Import Configuration

Script này tự động test và verify kết quả import:
1. Export từ công ty nguồn
2. Import vào công ty đích
3. Verify data trước và sau import
4. Tạo test report chi tiết

Usage:
    python test_import_verification.py [env] [source_company_id] [target_company_id] [target_company_name]
    
Example:
    python test_import_verification.py local 1 None "Test Company"
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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
        # Support test environment
        if env_type == 'test':
            url = os.getenv("ODOO_URL", "http://test.thepnamsaigon.com")
            db = os.getenv("ODOO_DB", "16.thepnamsaigon.03.11.2025")
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

def get_company_data_before_import(models, uid, password, db, company_id):
    """Lấy data của công ty TRƯỚC khi import"""
    print(f"\n📊 Collecting data BEFORE import for company ID: {company_id}...")
    
    data = {
        'accounts': [],
        'journals': [],
        'taxes': [],
        'fiscal_positions': [],
        'payment_terms': [],
        'bank_accounts': [],
        'pricelists': [],
        'sequences': [],
        'reconcile_models': [],
    }
    
    try:
        # Accounts
        accounts = models.execute_kw(
            db, uid, password,
            'account.account', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['code', 'name', 'account_type']}
        )
        data['accounts'] = accounts
        print(f"   ✓ Accounts: {len(accounts)}")
    except Exception as e:
        print(f"   ⚠️  Error getting accounts: {str(e)[:100]}")
    
    try:
        # Journals
        journals = models.execute_kw(
            db, uid, password,
            'account.journal', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'code', 'type']}
        )
        data['journals'] = journals
        print(f"   ✓ Journals: {len(journals)}")
    except Exception as e:
        print(f"   ⚠️  Error getting journals: {str(e)[:100]}")
    
    try:
        # Taxes
        taxes = models.execute_kw(
            db, uid, password,
            'account.tax', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'amount', 'type_tax_use']}
        )
        data['taxes'] = taxes
        print(f"   ✓ Taxes: {len(taxes)}")
    except Exception as e:
        print(f"   ⚠️  Error getting taxes: {str(e)[:100]}")
    
    try:
        # Fiscal Positions
        fps = models.execute_kw(
            db, uid, password,
            'account.fiscal.position', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active']}
        )
        data['fiscal_positions'] = fps
        print(f"   ✓ Fiscal Positions: {len(fps)}")
    except Exception as e:
        print(f"   ⚠️  Error getting fiscal positions: {str(e)[:100]}")
    
    try:
        # Payment Terms
        pts = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active']}
        )
        data['payment_terms'] = pts
        print(f"   ✓ Payment Terms: {len(pts)}")
    except Exception as e:
        print(f"   ⚠️  Error getting payment terms: {str(e)[:100]}")
    
    try:
        # Bank Accounts
        bank_accs = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['acc_number', 'acc_holder_name']}
        )
        data['bank_accounts'] = bank_accs
        print(f"   ✓ Bank Accounts: {len(bank_accs)}")
    except Exception as e:
        print(f"   ⚠️  Error getting bank accounts: {str(e)[:100]}")
    
    try:
        # Pricelists
        pricelists = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active']}
        )
        data['pricelists'] = pricelists
        print(f"   ✓ Pricelists: {len(pricelists)}")
    except Exception as e:
        print(f"   ⚠️  Error getting pricelists: {str(e)[:100]}")
    
    try:
        # Sequences
        sequences = models.execute_kw(
            db, uid, password,
            'ir.sequence', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'code']}
        )
        data['sequences'] = sequences
        print(f"   ✓ Sequences: {len(sequences)}")
    except Exception as e:
        print(f"   ⚠️  Error getting sequences: {str(e)[:100]}")
    
    try:
        # Reconcile Models
        rms = models.execute_kw(
            db, uid, password,
            'account.reconcile.model', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'rule_type']}
        )
        data['reconcile_models'] = rms
        print(f"   ✓ Reconcile Models: {len(rms)}")
    except Exception as e:
        print(f"   ⚠️  Error getting reconcile models: {str(e)[:100]}")
    
    return data

def get_company_data_after_import(models, uid, password, db, company_id):
    """Lấy data của công ty SAU khi import"""
    return get_company_data_before_import(models, uid, password, db, company_id)

def verify_import_results(models, uid, password, db, source_company_id, target_company_id, config):
    """Verify kết quả import chi tiết"""
    print(f"\n{'='*70}")
    print(f"🔍 DETAILED VERIFICATION")
    print(f"{'='*70}\n")
    
    results = {
        'accounts': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'journals': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'taxes': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'fiscal_positions': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'payment_terms': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'bank_accounts': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'pricelists': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'sequences': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
        'reconcile_models': {'status': 'pending', 'expected': 0, 'actual': 0, 'details': []},
    }
    
    # Verify Accounts
    print("📋 Verifying Accounts...")
    expected_accounts = config.get('chart_of_accounts', [])
    results['accounts']['expected'] = len(expected_accounts)
    
    try:
        actual_accounts = models.execute_kw(
            db, uid, password,
            'account.account', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['code', 'name', 'account_type']}
        )
        results['accounts']['actual'] = len(actual_accounts)
        
        # Check specific accounts
        expected_codes = {acc.get('code') for acc in expected_accounts}
        actual_codes = {acc.get('code') for acc in actual_accounts}
        missing_codes = expected_codes - actual_codes
        extra_codes = actual_codes - expected_codes
        
        if missing_codes:
            results['accounts']['details'].append(f"Missing codes: {list(missing_codes)[:10]}")
        if extra_codes:
            results['accounts']['details'].append(f"Extra codes: {list(extra_codes)[:10]}")
        
        if results['accounts']['actual'] >= results['accounts']['expected']:
            results['accounts']['status'] = '✅ PASS'
        else:
            results['accounts']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['accounts']['status']} Expected: {results['accounts']['expected']}, Actual: {results['accounts']['actual']}")
    except Exception as e:
        results['accounts']['status'] = '❌ ERROR'
        results['accounts']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Journals
    print("📝 Verifying Journals...")
    expected_journals = config.get('journals', [])
    results['journals']['expected'] = len(expected_journals)
    
    try:
        actual_journals = models.execute_kw(
            db, uid, password,
            'account.journal', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'code', 'type']}
        )
        results['journals']['actual'] = len(actual_journals)
        
        expected_codes = {j.get('code') for j in expected_journals if j.get('code')}
        actual_codes = {j.get('code') for j in actual_journals if j.get('code')}
        missing_codes = expected_codes - actual_codes
        
        if missing_codes:
            results['journals']['details'].append(f"Missing journal codes: {list(missing_codes)}")
        
        if results['journals']['actual'] >= results['journals']['expected']:
            results['journals']['status'] = '✅ PASS'
        else:
            results['journals']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['journals']['status']} Expected: {results['journals']['expected']}, Actual: {results['journals']['actual']}")
    except Exception as e:
        results['journals']['status'] = '❌ ERROR'
        results['journals']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Taxes
    print("💰 Verifying Taxes...")
    expected_taxes = config.get('taxes', [])
    results['taxes']['expected'] = len(expected_taxes)
    
    try:
        actual_taxes = models.execute_kw(
            db, uid, password,
            'account.tax', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'amount', 'type_tax_use']}
        )
        results['taxes']['actual'] = len(actual_taxes)
        
        expected_names = {t.get('name') for t in expected_taxes}
        actual_names = {t.get('name') for t in actual_taxes}
        missing_names = expected_names - actual_names
        
        if missing_names:
            results['taxes']['details'].append(f"Missing taxes: {list(missing_names)}")
        
        if results['taxes']['actual'] >= results['taxes']['expected']:
            results['taxes']['status'] = '✅ PASS'
        else:
            results['taxes']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['taxes']['status']} Expected: {results['taxes']['expected']}, Actual: {results['taxes']['actual']}")
    except Exception as e:
        results['taxes']['status'] = '❌ ERROR'
        results['taxes']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Fiscal Positions
    print("🌍 Verifying Fiscal Positions...")
    expected_fps = config.get('fiscal_positions', [])
    results['fiscal_positions']['expected'] = len(expected_fps)
    
    try:
        actual_fps = models.execute_kw(
            db, uid, password,
            'account.fiscal.position', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'active']}
        )
        results['fiscal_positions']['actual'] = len(actual_fps)
        
        if results['fiscal_positions']['actual'] >= results['fiscal_positions']['expected']:
            results['fiscal_positions']['status'] = '✅ PASS'
        else:
            results['fiscal_positions']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['fiscal_positions']['status']} Expected: {results['fiscal_positions']['expected']}, Actual: {results['fiscal_positions']['actual']}")
    except Exception as e:
        results['fiscal_positions']['status'] = '❌ ERROR'
        results['fiscal_positions']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Payment Terms
    print("💳 Verifying Payment Terms...")
    expected_pts = config.get('payment_terms', [])
    results['payment_terms']['expected'] = len(expected_pts)
    
    try:
        actual_pts = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'active']}
        )
        results['payment_terms']['actual'] = len(actual_pts)
        
        if results['payment_terms']['actual'] >= results['payment_terms']['expected']:
            results['payment_terms']['status'] = '✅ PASS'
        else:
            results['payment_terms']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['payment_terms']['status']} Expected: {results['payment_terms']['expected']}, Actual: {results['payment_terms']['actual']}")
    except Exception as e:
        results['payment_terms']['status'] = '❌ ERROR'
        results['payment_terms']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Bank Accounts
    print("🏦 Verifying Bank Accounts...")
    expected_bank = config.get('bank_accounts', [])
    results['bank_accounts']['expected'] = len(expected_bank)
    
    try:
        actual_bank = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['acc_number', 'acc_holder_name']}
        )
        results['bank_accounts']['actual'] = len(actual_bank)
        
        if results['bank_accounts']['actual'] >= results['bank_accounts']['expected']:
            results['bank_accounts']['status'] = '✅ PASS'
        else:
            results['bank_accounts']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['bank_accounts']['status']} Expected: {results['bank_accounts']['expected']}, Actual: {results['bank_accounts']['actual']}")
    except Exception as e:
        results['bank_accounts']['status'] = '❌ ERROR'
        results['bank_accounts']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Pricelists
    print("💰 Verifying Pricelists...")
    expected_pl = config.get('pricelists', [])
    results['pricelists']['expected'] = len(expected_pl)
    
    try:
        actual_pl = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'active']}
        )
        results['pricelists']['actual'] = len(actual_pl)
        
        if results['pricelists']['actual'] >= results['pricelists']['expected']:
            results['pricelists']['status'] = '✅ PASS'
        else:
            results['pricelists']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['pricelists']['status']} Expected: {results['pricelists']['expected']}, Actual: {results['pricelists']['actual']}")
    except Exception as e:
        results['pricelists']['status'] = '❌ ERROR'
        results['pricelists']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Sequences
    print("🔢 Verifying Sequences...")
    expected_seq = config.get('sequences', [])
    results['sequences']['expected'] = len(expected_seq)
    
    try:
        actual_seq = models.execute_kw(
            db, uid, password,
            'ir.sequence', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'code']}
        )
        results['sequences']['actual'] = len(actual_seq)
        
        if results['sequences']['actual'] >= results['sequences']['expected']:
            results['sequences']['status'] = '✅ PASS'
        else:
            results['sequences']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['sequences']['status']} Expected: {results['sequences']['expected']}, Actual: {results['sequences']['actual']}")
    except Exception as e:
        results['sequences']['status'] = '❌ ERROR'
        results['sequences']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Verify Reconcile Models
    print("🔄 Verifying Reconcile Models...")
    expected_rm = config.get('reconcile_models', [])
    results['reconcile_models']['expected'] = len(expected_rm)
    
    try:
        actual_rm = models.execute_kw(
            db, uid, password,
            'account.reconcile.model', 'search_read',
            [[('company_id', '=', target_company_id)]],
            {'fields': ['name', 'rule_type']}
        )
        results['reconcile_models']['actual'] = len(actual_rm)
        
        if results['reconcile_models']['actual'] >= results['reconcile_models']['expected']:
            results['reconcile_models']['status'] = '✅ PASS'
        else:
            results['reconcile_models']['status'] = '⚠️  PARTIAL'
        
        print(f"   {results['reconcile_models']['status']} Expected: {results['reconcile_models']['expected']}, Actual: {results['reconcile_models']['actual']}")
    except Exception as e:
        results['reconcile_models']['status'] = '❌ ERROR'
        results['reconcile_models']['details'].append(f"Error: {str(e)[:100]}")
        print(f"   ❌ Error: {str(e)[:100]}")
    
    return results

def test_workflows(models, uid, password, db, target_company_id):
    """Test các workflows cơ bản"""
    print(f"\n{'='*70}")
    print(f"🧪 TESTING WORKFLOWS")
    print(f"{'='*70}\n")
    
    workflow_results = {
        'create_invoice': {'status': 'pending', 'message': ''},
        'create_payment': {'status': 'pending', 'message': ''},
    }
    
    # Test: Tìm journal để tạo invoice
    print("📄 Testing Invoice Creation...")
    try:
        journals = models.execute_kw(
            db, uid, password,
            'account.journal', 'search',
            [[('company_id', '=', target_company_id), ('type', '=', 'sale')]]
        )
        if journals:
            workflow_results['create_invoice']['status'] = '✅ READY'
            workflow_results['create_invoice']['message'] = f"Found {len(journals)} sale journal(s) - Invoice creation should work"
            print(f"   ✅ Found {len(journals)} sale journal(s)")
        else:
            workflow_results['create_invoice']['status'] = '⚠️  WARNING'
            workflow_results['create_invoice']['message'] = "No sale journal found - Invoice creation may fail"
            print(f"   ⚠️  No sale journal found")
    except Exception as e:
        workflow_results['create_invoice']['status'] = '❌ ERROR'
        workflow_results['create_invoice']['message'] = f"Error: {str(e)[:100]}"
        print(f"   ❌ Error: {str(e)[:100]}")
    
    # Test: Tìm bank journal để tạo payment
    print("💸 Testing Payment Creation...")
    try:
        bank_journals = models.execute_kw(
            db, uid, password,
            'account.journal', 'search',
            [[('company_id', '=', target_company_id), ('type', '=', 'bank')]]
        )
        if bank_journals:
            workflow_results['create_payment']['status'] = '✅ READY'
            workflow_results['create_payment']['message'] = f"Found {len(bank_journals)} bank journal(s) - Payment creation should work"
            print(f"   ✅ Found {len(bank_journals)} bank journal(s)")
        else:
            workflow_results['create_payment']['status'] = '⚠️  WARNING'
            workflow_results['create_payment']['message'] = "No bank journal found - Payment creation may fail"
            print(f"   ⚠️  No bank journal found")
    except Exception as e:
        workflow_results['create_payment']['status'] = '❌ ERROR'
        workflow_results['create_payment']['message'] = f"Error: {str(e)[:100]}"
        print(f"   ❌ Error: {str(e)[:100]}")
    
    return workflow_results

def generate_test_report(test_results, output_file):
    """Tạo test report chi tiết"""
    report = f"""# Test Report - Import Verification
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Test Summary

### Overall Status
"""
    
    # Count statuses
    pass_count = sum(1 for r in test_results['verification'].values() if '✅' in r.get('status', ''))
    partial_count = sum(1 for r in test_results['verification'].values() if '⚠️' in r.get('status', ''))
    error_count = sum(1 for r in test_results['verification'].values() if '❌' in r.get('status', ''))
    
    total_tests = len(test_results['verification'])
    pass_rate = (pass_count / total_tests * 100) if total_tests > 0 else 0
    
    report += f"""
- **Total Tests**: {total_tests}
- **✅ Passed**: {pass_count}
- **⚠️  Partial**: {partial_count}
- **❌ Errors**: {error_count}
- **Pass Rate**: {pass_rate:.1f}%

## Detailed Results

### Verification Results

"""
    
    for model, result in test_results['verification'].items():
        status = result.get('status', 'UNKNOWN')
        expected = result.get('expected', 0)
        actual = result.get('actual', 0)
        details = result.get('details', [])
        
        report += f"""
#### {model.replace('_', ' ').title()}
- **Status**: {status}
- **Expected**: {expected}
- **Actual**: {actual}
"""
        if details:
            report += f"- **Details**:\n"
            for detail in details:
                report += f"  - {detail}\n"
    
    report += f"""
### Workflow Tests

"""
    
    for workflow, result in test_results['workflows'].items():
        status = result.get('status', 'UNKNOWN')
        message = result.get('message', '')
        report += f"""
#### {workflow.replace('_', ' ').title()}
- **Status**: {status}
- **Message**: {message}
"""
    
    report += f"""
## Recommendations

"""
    
    if error_count > 0:
        report += "- ⚠️  Some tests failed. Please review the errors above.\n"
    
    if partial_count > 0:
        report += "- ⚠️  Some tests passed partially. Verify manually.\n"
    
    if pass_rate == 100:
        report += "- ✅ All tests passed! Import is successful.\n"
    
    report += f"""
## Next Steps

1. Review the verification results above
2. Test manually in Odoo UI:
   - Accounting > Configuration > Chart of Accounts
   - Accounting > Configuration > Journals
   - Accounting > Configuration > Taxes
   - Create a test invoice
   - Create a test payment
3. If all tests pass, proceed with manual setup steps
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Test report saved to: {output_file}")

def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("python test_import_verification.py [env] [source_company_id] [target_company_id] [target_company_name]")
        print("\nExample:")
        print("  python test_import_verification.py test 1 2 'Company Name'  # Import vào company ID 2")
        print("  python test_import_verification.py local 1 None 'Test Company'  # Tạo công ty mới")
        print("="*70)
        return 1
    
    env_type = sys.argv[1]
    source_company_id = int(sys.argv[2])
    target_company_id = None
    if len(sys.argv) > 3 and sys.argv[3].lower() not in ['none', 'null', '']:
        try:
            target_company_id = int(sys.argv[3])
        except ValueError:
            target_company_id = None
    target_company_name = sys.argv[4] if len(sys.argv) > 4 else "Test Company"
    
    print("="*70)
    print("🧪 AUTOMATED TEST & VERIFICATION")
    print("="*70)
    print("Environment: {}".format(env_type))
    print("Source Company ID: {}".format(source_company_id))
    if target_company_id:
        print("Target Company ID: {} (existing company - will import only)".format(target_company_id))
        print("Target Company Name: {} (ignored - using existing company)".format(target_company_name))
    else:
        print("Target Company ID: New (will be created)")
        print("Target Company Name: {}".format(target_company_name))
    print("="*70 + "\n")
    
    # Connect
    print("🔗 Connecting to Odoo...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})\n")
    
    # Step 1: Export
    print("="*70)
    print("STEP 1: EXPORT FROM SOURCE COMPANY")
    print("="*70 + "\n")
    
    # Import export function
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from export_accounting_config import export_accounting_config
        config = export_accounting_config(models, uid, password, db, source_company_id)
        if not config:
            print("❌ Export failed!")
            return 1
    except Exception as e:
        print(f"❌ Error importing export function: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Save export file
    export_file = Path(__file__).parent / f'accounting_config_company_{source_company_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(export_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ Export saved to: {export_file.name}\n")
    
    # Step 2: Get data BEFORE import
    if target_company_id:
        print("="*70)
        print("STEP 2: DATA BEFORE IMPORT")
        print("="*70 + "\n")
        data_before = get_company_data_before_import(models, uid, password, db, target_company_id)
    else:
        data_before = None
    
    # Step 3: Import
    print("\n" + "="*70)
    print("STEP 3: IMPORT TO TARGET COMPANY")
    print("="*70 + "\n")
    
    # Import import function
    try:
        from import_accounting_config import (
            create_or_get_company,
            import_chart_of_accounts,
            import_journals,
            import_taxes,
            import_fiscal_positions,
            import_payment_terms,
            import_company_settings,
            import_config_parameters,
            import_master_data,
        )
    except Exception as e:
        print(f"❌ Error importing import functions: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Get or create company
    if target_company_id:
        # Use existing company - verify it exists
        print("📋 Using existing company ID: {}".format(target_company_id))
        try:
            company_info = models.execute_kw(
                db, uid, password,
                'res.company', 'read',
                [[target_company_id]],
                {'fields': ['id', 'name']}
            )
            if company_info:
                company_id = target_company_id
                print("✅ Company found: {} (ID: {})".format(company_info[0].get('name', 'N/A'), company_id))
            else:
                print("❌ Company ID {} not found!".format(target_company_id))
                return 1
        except Exception as e:
            print("❌ Error checking company: {}".format(str(e)))
            return 1
    else:
        # Create new company
        company_id = create_or_get_company(
            models, uid, password, db,
            config['company'],
            None,
            target_company_name
        )
        
        if not company_id:
            print("❌ Failed to create company")
            return 1
    
    # ID mapping
    id_mapping = {
        'account': {},
        'journal': {},
        'tax': {},
        'tax_group': {},
    }
    
    # Import in order
    import_chart_of_accounts(
        models, uid, password, db,
        config.get('chart_of_accounts', []),
        config.get('account_groups', []),
        company_id,
        id_mapping
    )
    
    import_journals(
        models, uid, password, db,
        config.get('journals', []),
        company_id,
        id_mapping
    )
    
    import_taxes(
        models, uid, password, db,
        config.get('taxes', []),
        config.get('tax_groups', []),
        company_id,
        id_mapping
    )
    
    import_fiscal_positions(
        models, uid, password, db,
        config.get('fiscal_positions', []),
        company_id,
        id_mapping
    )
    
    import_payment_terms(
        models, uid, password, db,
        config.get('payment_terms', []),
        company_id,
        id_mapping
    )
    
    import_company_settings(
        models, uid, password, db,
        config.get('company', {}),
        company_id
    )
    
    import_config_parameters(
        models, uid, password, db,
        config.get('config_parameters', [])
    )
    
    import_master_data(
        models, uid, password, db,
        config,
        company_id,
        id_mapping
    )
    
    # Step 4: Get data AFTER import
    print("\n" + "="*70)
    print("STEP 4: DATA AFTER IMPORT")
    print("="*70 + "\n")
    data_after = get_company_data_after_import(models, uid, password, db, company_id)
    
    # Step 5: Verify
    print("\n" + "="*70)
    print("STEP 5: VERIFICATION")
    print("="*70 + "\n")
    verification_results = verify_import_results(
        models, uid, password, db,
        source_company_id,
        company_id,
        config
    )
    
    # Step 6: Test workflows
    workflow_results = test_workflows(models, uid, password, db, company_id)
    
    # Step 7: Generate report
    print("\n" + "="*70)
    print("STEP 6: GENERATING TEST REPORT")
    print("="*70 + "\n")
    
    test_results = {
        'source_company_id': source_company_id,
        'target_company_id': company_id,
        'target_company_name': target_company_name,
        'export_file': export_file.name,
        'data_before': data_before if target_company_id else None,
        'data_after': data_after,
        'verification': verification_results,
        'workflows': workflow_results,
    }
    
    report_file = Path(__file__).parent / f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    generate_test_report(test_results, report_file)
    
    # Final summary
    print("\n" + "="*70)
    print("✅ TEST COMPLETED")
    print("="*70 + "\n")
    
    pass_count = sum(1 for r in verification_results.values() if '✅' in r.get('status', ''))
    total = len(verification_results)
    
    print("📊 Test Results: {}/{} tests passed".format(pass_count, total))
    print("📄 Report: {}".format(report_file.name))
    print("\n💡 Review the test report for detailed results\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
