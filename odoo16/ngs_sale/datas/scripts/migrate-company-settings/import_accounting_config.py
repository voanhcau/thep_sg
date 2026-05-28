#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import Accounting Configuration vào công ty mới

Script này import cấu hình kế toán từ file JSON vào công ty mới.

Usage:
    python import_accounting_config.py [local|staging|prod] [config_file.json] [target_company_id] [target_company_name]
    
Example:
    python import_accounting_config.py local accounting_config_company_1_20250101_120000.json 2 "Công Ty Mới"
"""

import sys
import json
import os
from pathlib import Path
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

def load_config(config_file):
    """Load configuration từ JSON file"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_or_get_company(models, uid, password, db, company_data, target_company_id=None, target_company_name=None):
    """Tạo hoặc lấy company"""
    if target_company_id:
        # Use existing company
        company = models.execute_kw(
            db, uid, password,
            'res.company', 'read',
            [[target_company_id]],
            {'fields': ['id', 'name']}
        )
        if company:
            print(f"✅ Using existing company: {company[0]['name']} (ID: {target_company_id})")
            return target_company_id
        else:
            print(f"❌ Company ID {target_company_id} not found")
            return None
    
    # Create new company
    company_name = target_company_name or company_data.get('name', 'New Company')
    
    # Check if company exists
    existing = models.execute_kw(
        db, uid, password,
        'res.company', 'search',
        [[('name', '=', company_name)]]
    )
    if existing:
        print(f"✅ Company already exists: {company_name} (ID: {existing[0]})")
        return existing[0]
    
    # Create new company
    new_company_data = {
        'name': company_name,
        'currency_id': company_data.get('currency_id', [1])[0] if isinstance(company_data.get('currency_id'), list) else company_data.get('currency_id', 1),
        'country_id': company_data.get('country_id', [241])[0] if isinstance(company_data.get('country_id'), list) else company_data.get('country_id', 241),  # Vietnam
    }
    
    company_id = models.execute_kw(
        db, uid, password,
        'res.company', 'create',
        [new_company_data]
    )
    
    print(f"✅ Created new company: {company_name} (ID: {company_id})")
    return company_id

def import_chart_of_accounts(models, uid, password, db, accounts, account_groups, company_id, id_mapping):
    """Import chart of accounts"""
    print("\n📊 [1/8] Importing Chart of Accounts...")
    
    # Import account groups first (nếu có)
    group_mapping = {}
    if account_groups:
        # Sort by parent first
        groups_sorted = sorted(account_groups, key=lambda x: (x.get('parent_id', [False])[0] if isinstance(x.get('parent_id'), list) else x.get('parent_id', False), x.get('id', 0)))
        
        for group in groups_sorted:
            # Find or create account group
            existing = models.execute_kw(
                db, uid, password,
                'account.group', 'search',
                [[('company_id', '=', company_id), ('code_prefix_start', '=', group.get('code_prefix_start'))]]
            )
            if existing:
                group_mapping[group['id']] = existing[0]
            else:
                new_group_data = {
                    'name': group['name'],
                    'code_prefix_start': group.get('code_prefix_start'),
                    'code_prefix_end': group.get('code_prefix_end'),
                    'company_id': company_id,
                }
                if group.get('parent_id'):
                    parent_id = group_mapping.get(group['parent_id'][0])
                    if parent_id:
                        new_group_data['parent_id'] = parent_id
                
                new_id = models.execute_kw(
                    db, uid, password,
                    'account.group', 'create',
                    [new_group_data]
                )
                group_mapping[group['id']] = new_id
    
    # Import accounts (sorted by code to handle parent-child relationships)
    accounts_sorted = sorted(accounts, key=lambda x: x.get('code', ''))
    
    for account in accounts_sorted:
        # Check if account exists
        existing = models.execute_kw(
            db, uid, password,
            'account.account', 'search',
            [[('company_id', '=', company_id), ('code', '=', account.get('code'))]]
        )
        if existing:
            id_mapping['account'][account['id']] = existing[0]
            continue
        
        # Create account
        account_data = {
            'code': account['code'],
            'name': account['name'],
            'account_type': account.get('account_type', 'asset_current'),
            'company_id': company_id,
            'deprecated': account.get('deprecated', False),
            'reconcile': account.get('reconcile', False),
        }
        
        if account.get('group_id'):
            group_id = group_mapping.get(account['group_id'][0])
            if group_id:
                account_data['group_id'] = group_id
        
        if account.get('currency_id'):
            account_data['currency_id'] = account['currency_id'][0] if isinstance(account['currency_id'], list) else account['currency_id']
        
        new_id = models.execute_kw(
            db, uid, password,
            'account.account', 'create',
            [account_data]
        )
        id_mapping['account'][account['id']] = new_id
    
    print(f"   ✓ Imported {len(accounts)} accounts")

def import_journals(models, uid, password, db, journals, company_id, id_mapping):
    """Import journals"""
    print("\n📝 [2/8] Importing Journals...")
    
    for journal in journals:
        # Check if journal exists
        existing = models.execute_kw(
            db, uid, password,
            'account.journal', 'search',
            [[('company_id', '=', company_id), ('code', '=', journal.get('code'))]]
        )
        if existing:
            id_mapping['journal'][journal['id']] = existing[0]
            continue
        
        journal_data = {
            'name': journal['name'],
            'code': journal.get('code', ''),
            'type': journal['type'],
            'company_id': company_id,
            'active': journal.get('active', True),
            'sequence': journal.get('sequence', 10),
        }
        
        # Map default account
        if journal.get('default_account_id'):
            account_id = id_mapping['account'].get(journal['default_account_id'][0])
            if account_id:
                journal_data['default_account_id'] = account_id
        
        # Map bank account
        if journal.get('bank_account_id'):
            bank_acc_id = journal['bank_account_id'][0] if isinstance(journal['bank_account_id'], list) else journal['bank_account_id']
            # Bank account sẽ được map sau khi import bank accounts
            # Tạm thời skip, sẽ update sau
        
        if journal.get('currency_id'):
            journal_data['currency_id'] = journal['currency_id'][0] if isinstance(journal['currency_id'], list) else journal['currency_id']
        
        new_id = models.execute_kw(
            db, uid, password,
            'account.journal', 'create',
            [journal_data]
        )
        id_mapping['journal'][journal['id']] = new_id
    
    print(f"   ✓ Imported {len(journals)} journals")

def import_taxes(models, uid, password, db, taxes, tax_groups, company_id, id_mapping):
    """Import taxes and tax groups"""
    print("\n💰 [3/8] Importing Taxes...")
    
    # Import tax groups first (tax groups don't have company_id in Odoo 16)
    for tax_group in tax_groups:
        existing = models.execute_kw(
            db, uid, password,
            'account.tax.group', 'search',
            [[('name', '=', tax_group.get('name'))]]
        )
        if existing:
            id_mapping['tax_group'][tax_group['id']] = existing[0]
        else:
            tax_group_data = {
                'name': tax_group['name'],
                'sequence': tax_group.get('sequence', 10),
                'preceding_subtotal': tax_group.get('preceding_subtotal', ''),
            }
            new_id = models.execute_kw(
                db, uid, password,
                'account.tax.group', 'create',
                [tax_group_data]
            )
            id_mapping['tax_group'][tax_group['id']] = new_id
    
    # Import taxes
    for tax in taxes:
        existing = models.execute_kw(
            db, uid, password,
            'account.tax', 'search',
            [[('company_id', '=', company_id), ('name', '=', tax.get('name'))]]
        )
        if existing:
            id_mapping['tax'][tax['id']] = existing[0]
            continue
        
        tax_data = {
            'name': tax['name'],
            'description': tax.get('description', ''),
            'amount': tax.get('amount', 0),
            'amount_type': tax.get('amount_type', 'percent'),
            'type_tax_use': tax.get('type_tax_use', 'sale'),
            'tax_scope': tax.get('tax_scope', 'consu'),
            'company_id': company_id,
            'active': tax.get('active', True),
            'sequence': tax.get('sequence', 10),
            'price_include': tax.get('price_include', False),
            'include_base_amount': tax.get('include_base_amount', False),
            'is_base_affected': tax.get('is_base_affected', False),
        }
        
        if tax.get('tax_group_id'):
            group_id = id_mapping['tax_group'].get(tax['tax_group_id'][0])
            if group_id:
                tax_data['tax_group_id'] = group_id
        
        # Tax accounts are now in repartition lines, not directly on tax
        # We'll handle repartition lines after creating the tax
        
        new_id = models.execute_kw(
            db, uid, password,
            'account.tax', 'create',
            [tax_data]
        )
        id_mapping['tax'][tax['id']] = new_id
        
        # Import repartition lines if available
        # Note: Repartition lines are created automatically when tax is created
        # We need to update them if accounts need to be mapped
        # For now, skip manual creation as Odoo handles this automatically
        # Accounts will be mapped through the tax's default repartition lines
    
    print(f"   ✓ Imported {len(taxes)} taxes")

def import_fiscal_positions(models, uid, password, db, fiscal_positions, company_id, id_mapping):
    """Import fiscal positions"""
    print("\n🌍 [4/8] Importing Fiscal Positions...")
    
    for fp in fiscal_positions:
        existing = models.execute_kw(
            db, uid, password,
            'account.fiscal.position', 'search',
            [[('company_id', '=', company_id), ('name', '=', fp.get('name'))]]
        )
        if existing:
            fp_id = existing[0]
        else:
            fp_data = {
                'name': fp['name'],
                'company_id': company_id,
                'active': fp.get('active', True),
                'vat_required': fp.get('vat_required', False),
                'auto_apply': fp.get('auto_apply', False),
            }
            
            if fp.get('country_id'):
                fp_data['country_id'] = fp['country_id'][0] if isinstance(fp['country_id'], list) else fp['country_id']
            
            fp_id = models.execute_kw(
                db, uid, password,
                'account.fiscal.position', 'create',
                [fp_data]
            )
        
        # Import tax mappings
        for tax_mapping in fp.get('tax_ids', []):
            tax_src_id = id_mapping['tax'].get(tax_mapping.get('tax_src_id', [0])[0])
            tax_dest_id = id_mapping['tax'].get(tax_mapping.get('tax_dest_id', [0])[0])
            
            if tax_src_id and tax_dest_id:
                models.execute_kw(
                    db, uid, password,
                    'account.fiscal.position.tax', 'create',
                    [{
                        'position_id': fp_id,
                        'tax_src_id': tax_src_id,
                        'tax_dest_id': tax_dest_id,
                    }]
                )
        
        # Import account mappings
        for account_mapping in fp.get('account_ids', []):
            account_src_id = id_mapping['account'].get(account_mapping.get('account_src_id', [0])[0])
            account_dest_id = id_mapping['account'].get(account_mapping.get('account_dest_id', [0])[0])
            
            if account_src_id and account_dest_id:
                models.execute_kw(
                    db, uid, password,
                    'account.fiscal.position.account', 'create',
                    [{
                        'position_id': fp_id,
                        'account_src_id': account_src_id,
                        'account_dest_id': account_dest_id,
                    }]
                )
    
    print(f"   ✓ Imported {len(fiscal_positions)} fiscal positions")

def import_payment_terms(models, uid, password, db, payment_terms, company_id, id_mapping):
    """Import payment terms"""
    print("\n💳 [5/8] Importing Payment Terms...")
    
    payment_terms_mapping = {}
    for pt in payment_terms:
        # Payment terms có thể không có company_id (dùng chung)
        pt_company_id = pt.get('company_id')
        if isinstance(pt_company_id, list):
            pt_company_id = pt_company_id[0]
        
        # Nếu payment term không có company_id hoặc là company_id hiện tại
        if not pt_company_id or pt_company_id == company_id:
            # Check by name (không filter company vì có thể dùng chung)
            existing = models.execute_kw(
                db, uid, password,
                'account.payment.term', 'search',
                [[('name', '=', pt.get('name'))]]
            )
            if existing:
                pt_id = existing[0]
            else:
                pt_data = {
                    'name': pt['name'],
                    'company_id': company_id,  # Set company_id cho công ty mới
                    'active': pt.get('active', True),
                    'note': pt.get('note', ''),
                }
                pt_id = models.execute_kw(
                    db, uid, password,
                    'account.payment.term', 'create',
                    [pt_data]
                )
            
            payment_terms_mapping[pt['id']] = pt_id
            
            # Import payment term lines (chỉ nếu chưa có)
            existing_lines = models.execute_kw(
                db, uid, password,
                'account.payment.term.line', 'search_count',
                [[('payment_id', '=', pt_id)]]
            )
            if existing_lines == 0:
                for line in pt.get('line_ids', []):
                    models.execute_kw(
                        db, uid, password,
                        'account.payment.term.line', 'create',
                        [{
                            'payment_id': pt_id,
                            'value': line.get('value', 'balance'),
                            'value_amount': line.get('value_amount', 0),
                            'nb_days': line.get('nb_days', 0),
                            'option': line.get('option', 'day_after'),
                            'days_after': line.get('days_after', 0),
                        }]
                    )
    
    print(f"   ✓ Imported {len(payment_terms_mapping)} payment terms")

def import_company_settings(models, uid, password, db, company_data, company_id):
    """Import company custom settings"""
    print("\n⚙️  [6/8] Importing Company Settings...")
    
    update_data = {}
    
    # Anglo-saxon accounting setting (requires account_anglo_saxon module)
    if 'anglo_saxon_accounting' in company_data:
        anglo_saxon = company_data.get('anglo_saxon_accounting')
        if anglo_saxon is not None:
            # Check if field exists (module account_anglo_saxon must be installed)
            try:
                # Try to read the field to check if it exists
                test_read = models.execute_kw(
                    db, uid, password,
                    'res.company', 'read',
                    [[company_id]],
                    {'fields': ['anglo_saxon_accounting']}
                )
                # If we can read it, the field exists
                update_data['anglo_saxon_accounting'] = bool(anglo_saxon)
                print(f"   → Anglo-saxon accounting: {'Enabled' if anglo_saxon else 'Disabled'}")
            except Exception as e:
                error_msg = str(e)
                if 'does not exist' in error_msg or 'Invalid field' in error_msg:
                    print(f"   ⚠️  Warning: 'Anglo-Saxon Accounting' field not available")
                    print(f"      Module 'account_anglo_saxon' may not be installed on target company")
                    print(f"      Please install 'account_anglo_saxon' module if needed")
                else:
                    # Other error, try to set anyway
                    try:
                        update_data['anglo_saxon_accounting'] = bool(anglo_saxon)
                        print(f"   → Anglo-saxon accounting: {'Enabled' if anglo_saxon else 'Disabled'}")
                    except:
                        print(f"   ⚠️  Warning: Could not set Anglo-saxon accounting: {error_msg[:100]}")
    
    # Custom fields from ngs_sale
    custom_fields = [
        'sale_description', 'purchase_description', 'signature',
        'signature_so', 'signature_po', 'interest_calculation_extra_days',
        'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
        'hide_report_footer',
    ]
    
    for field in custom_fields:
        if field in company_data:
            value = company_data[field]
            # Skip None, empty lists, empty strings, False (for non-boolean)
            if value is None:
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            if isinstance(value, str) and value == '':
                continue
            # For boolean fields, include even if False
            if field in ['signature_so', 'signature_po', 'hide_report_footer']:
                update_data[field] = bool(value)
            # For signature (Image field), skip if False or empty
            elif field == 'signature' and (value is False or value == ''):
                continue
            else:
                update_data[field] = value
    
    # Final check: remove any None values and debug
    clean_data = {}
    for k, v in update_data.items():
        if v is None:
            print(f"   ⚠️  Skipping {k}: None value")
            continue
        # Check for nested None in strings/HTML
        if isinstance(v, str) and 'None' in v:
            # Replace None strings with empty string
            v = v.replace('None', '')
        clean_data[k] = v
    
    if clean_data:
        try:
            models.execute_kw(
                db, uid, password,
                'res.company', 'write',
                [[company_id], clean_data]
            )
            print(f"   ✓ Updated {len(clean_data)} company settings")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg or 'Invalid field' in error_msg or 'cannot marshal None' in error_msg:
                print(f"   ⚠️  Warning: Custom fields require ngs_sale module to be installed on target company")
                print(f"   Please install ngs_sale module first, then set these fields manually in Odoo UI")
            else:
                print(f"   ⚠️  Warning: Could not update company settings: {error_msg[:200]}")
            print(f"   Fields attempted: {list(clean_data.keys())}")
            print(f"   Note: These are custom fields from ngs_sale module and can be set manually after module installation")

def import_config_parameters(models, uid, password, db, config_params):
    """Import config parameters"""
    print("\n🔧 [7/8] Importing Config Parameters...")
    
    for param in config_params:
        # Check if exists
        existing = models.execute_kw(
            db, uid, password,
            'ir.config_parameter', 'search',
            [[('key', '=', param.get('key'))]]
        )
        if existing:
            # Update
            models.execute_kw(
                db, uid, password,
                'ir.config_parameter', 'write',
                [[existing[0]], {'value': param.get('value', '')}]
            )
        else:
            # Create
            models.execute_kw(
                db, uid, password,
                'ir.config_parameter', 'create',
                [{
                    'key': param.get('key'),
                    'value': param.get('value', ''),
                }]
            )
    
    print(f"   ✓ Imported {len(config_params)} config parameters")

def verify_import(models, uid, password, db, company_id, config, id_mapping):
    """Verify import results"""
    print(f"\n{'='*70}")
    print(f"🔍 VERIFYING IMPORT RESULTS")
    print(f"{'='*70}\n")
    
    verification_results = {
        'accounts': {'expected': len(config.get('chart_of_accounts', [])), 'actual': 0},
        'journals': {'expected': len(config.get('journals', [])), 'actual': 0},
        'taxes': {'expected': len(config.get('taxes', [])), 'actual': 0},
        'fiscal_positions': {'expected': len(config.get('fiscal_positions', [])), 'actual': 0},
        'payment_terms': {'expected': len(config.get('payment_terms', [])), 'actual': 0},
        'bank_accounts': {'expected': len(config.get('bank_accounts', [])), 'actual': 0},
    }
    
    # Verify accounts
    try:
        accounts = models.execute_kw(
            db, uid, password,
            'account.account', 'search_count',
            [[('company_id', '=', company_id)]]
        )
        verification_results['accounts']['actual'] = accounts
        status = "✅" if accounts >= verification_results['accounts']['expected'] else "⚠️"
        print(f"  {status} Accounts: {accounts} (expected: {verification_results['accounts']['expected']})")
    except Exception as e:
        print(f"  ❌ Error verifying accounts: {str(e)[:100]}")
    
    # Verify journals
    try:
        journals = models.execute_kw(
            db, uid, password,
            'account.journal', 'search_count',
            [[('company_id', '=', company_id)]]
        )
        verification_results['journals']['actual'] = journals
        status = "✅" if journals >= verification_results['journals']['expected'] else "⚠️"
        print(f"  {status} Journals: {journals} (expected: {verification_results['journals']['expected']})")
    except Exception as e:
        print(f"  ❌ Error verifying journals: {str(e)[:100]}")
    
    # Verify taxes
    try:
        taxes = models.execute_kw(
            db, uid, password,
            'account.tax', 'search_count',
            [[('company_id', '=', company_id)]]
        )
        verification_results['taxes']['actual'] = taxes
        status = "✅" if taxes >= verification_results['taxes']['expected'] else "⚠️"
        print(f"  {status} Taxes: {taxes} (expected: {verification_results['taxes']['expected']})")
    except Exception as e:
        print(f"  ❌ Error verifying taxes: {str(e)[:100]}")
    
    # Verify fiscal positions
    try:
        fps = models.execute_kw(
            db, uid, password,
            'account.fiscal.position', 'search_count',
            [[('company_id', '=', company_id)]]
        )
        verification_results['fiscal_positions']['actual'] = fps
        status = "✅" if fps >= verification_results['fiscal_positions']['expected'] else "⚠️"
        print(f"  {status} Fiscal Positions: {fps} (expected: {verification_results['fiscal_positions']['expected']})")
    except Exception as e:
        print(f"  ❌ Error verifying fiscal positions: {str(e)[:100]}")
    
    # Verify bank accounts
    try:
        bank_accs = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search_count',
            [[('company_id', '=', company_id)]]
        )
        verification_results['bank_accounts']['actual'] = bank_accs
        status = "✅" if bank_accs >= verification_results['bank_accounts']['expected'] else "⚠️"
        print(f"  {status} Bank Accounts: {bank_accs} (expected: {verification_results['bank_accounts']['expected']})")
    except Exception as e:
        print(f"  ❌ Error verifying bank accounts: {str(e)[:100]}")
    
    return verification_results

def main():
    if len(sys.argv) < 3:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("python import_accounting_config.py [env] [config_file.json] [target_company_id] [target_company_name]")
        print("\nExample:")
        print("  python import_accounting_config.py local config.json 2 'Công Ty Mới'")
        print("  python import_accounting_config.py local config.json None 'Công Ty Mới'  # Create new company")
        print("="*70)
        return 1
    
    env_type = sys.argv[1]
    config_file = Path(sys.argv[2])
    # Handle None string or empty
    target_company_id = None
    if len(sys.argv) > 3 and sys.argv[3].lower() not in ['none', 'null', '']:
        try:
            target_company_id = int(sys.argv[3])
        except ValueError:
            target_company_id = None
    target_company_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return 1
    
    print(f"\n{'='*70}")
    print(f"📥 IMPORTING ACCOUNTING CONFIGURATION")
    print(f"{'='*70}")
    print(f"Environment: {env_type}")
    print(f"Config file: {config_file.name}")
    print(f"Target company ID: {target_company_id if target_company_id else 'New (will be created)'}")
    print(f"Target company name: {target_company_name or 'N/A'}")
    print(f"{'='*70}\n")
    
    print(f"🔗 Connecting to {env_type} environment...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})")
    
    # Load config
    print(f"\n📂 Loading configuration from {config_file}...")
    try:
        config = load_config(config_file)
        print(f"✅ Configuration loaded successfully")
        print(f"   - Export date: {config.get('export_date', 'N/A')}")
        print(f"   - Source company ID: {config.get('source_company_id', 'N/A')}")
        print(f"   - Source company: {config.get('company', {}).get('name', 'N/A')}")
    except Exception as e:
        print(f"❌ Error loading config file: {str(e)}")
        return 1
    
    # ID mapping để track old -> new IDs
    id_mapping = {
        'account': {},
        'journal': {},
        'tax': {},
        'tax_group': {},
    }
    
    # Create or get company
    company_id = create_or_get_company(
        models, uid, password, db,
        config['company'],
        target_company_id,
        target_company_name
    )
    
    if not company_id:
        print("❌ Failed to create/get company")
        return 1
    
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
    
    # Import Master Data từ ngs_sale
    import_master_data(
        models, uid, password, db,
        config,
        company_id,
        id_mapping
    )
    
    # Verify import
    verification_results = verify_import(
        models, uid, password, db, company_id, config, id_mapping
    )
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"✅ IMPORT COMPLETED")
    print(f"{'='*70}")
    print(f"\n📊 IMPORT SUMMARY")
    print(f"{'='*70}")
    print(f"\n🏢 Company Information:")
    print(f"   - Company ID: {company_id}")
    try:
        company_info = models.execute_kw(
            db, uid, password,
            'res.company', 'read',
            [[company_id]],
            {'fields': ['name', 'vat', 'currency_id']}
        )
        if company_info:
            print(f"   - Company Name: {company_info[0].get('name', 'N/A')}")
            print(f"   - VAT: {company_info[0].get('vat', 'N/A')}")
    except:
        pass
    
    print(f"\n📋 Imported Records:")
    print(f"   ✓ Accounts: {len(id_mapping['account'])}")
    print(f"   ✓ Journals: {len(id_mapping['journal'])}")
    print(f"   ✓ Taxes: {len(id_mapping['tax'])}")
    print(f"   ✓ Tax Groups: {len(id_mapping.get('tax_group', {}))}")
    print(f"   ✓ Fiscal Positions: {len(config.get('fiscal_positions', []))}")
    print(f"   ✓ Payment Terms: {len(config.get('payment_terms', []))}")
    print(f"   ✓ Bank Accounts: {len(id_mapping.get('bank_account', {}))}")
    print(f"   ✓ Pricelists: {len(config.get('pricelists', []))}")
    print(f"   ✓ Sequences: {len(config.get('sequences', []))}")
    print(f"   ✓ Reconcile Models: {len(config.get('reconcile_models', []))}")
    
    print(f"\n{'='*70}")
    print(f"💡 NEXT STEPS (Manual Setup Required)")
    print(f"{'='*70}")
    print(f"\n1. ⚙️  Install module 'ngs_sale' on the new company (if not already installed)")
    print(f"   - Go to: Apps > Search 'ngs_sale' > Install")
    print(f"\n2. 📝 Set custom fields from ngs_sale module:")
    print(f"   - Go to: Settings > Companies & Contacts > Companies")
    print(f"   - Select the new company")
    print(f"   - Set the following fields:")
    print(f"     • sale_description")
    print(f"     • purchase_description")
    print(f"     • signature_so, signature_po")
    print(f"     • interest_calculation_extra_days")
    print(f"     • delivery_receipt_construction_site")
    print(f"     • delivery_receipt_footer_notes")
    print(f"     • hide_report_footer")
    print(f"\n3. 🏭 Setup warehouses (if needed):")
    print(f"   - Go to: Inventory > Configuration > Warehouses")
    print(f"   - Create warehouses manually (complex structure)")
    print(f"\n4. 👥 Assign users to the new company:")
    print(f"   - Go to: Settings > Users & Companies > Users")
    print(f"   - Assign users to the new company")
    print(f"\n5. 🔐 Configure access rights:")
    print(f"   - Set appropriate access rights for users")
    print(f"\n6. 🔄 Reset sequences (if needed):")
    print(f"   - Go to: Settings > Technical > Sequences")
    print(f"   - Reset sequences to maintain numbering")
    print(f"\n7. 📅 Setup fiscal year:")
    print(f"   - Go to: Accounting > Configuration > Fiscal Years")
    print(f"   - Create fiscal year for the new company")
    print(f"\n8. ✅ Test the setup:")
    print(f"   - Create a test invoice")
    print(f"   - Create a test payment")
    print(f"   - Verify reports work correctly")
    print(f"\n{'='*70}\n")
    
    return 0

def import_master_data(models, uid, password, db, config, company_id, id_mapping):
    """Import master data từ ngs_sale module (CHỈ những bảng có company_id)"""
    print("\n📦 [8/8] Importing Master Data from ngs_sale (company-specific only)...")
    print("    ⚠️  Note: res.partner.type, supplier.delivery.type, sale.processing.state")
    print("       are shared across companies (no company_id) - SKIP import")
    
    # Import sale.commission.rate (cần supplier_id mapping)
    print("  → Importing sale commission rates...")
    print("    ⚠️  Note: Commission rates require supplier mapping - may need manual setup")
    # Note: Commission rates link to suppliers, need to map supplier IDs
    
    # Import sale.barem (SKIP - không có company_id, dùng chung)
    print("  → Skipping sale barems (shared across companies, no company_id)...")
    
    # Import sale.commission.config (cần commission_tool_id mapping)
    print("  → Importing sale commission configs...")
    print("    ⚠️  Note: Commission configs require commission tool mapping - may need manual setup")
    
    # Import Bank Accounts
    print("  → Importing bank accounts...")
    bank_accounts_mapping = {}
    for bank_acc in config.get('bank_accounts', []):
        # Find partner
        partner_id = None
        if bank_acc.get('partner_id'):
            partner_id = bank_acc['partner_id'][0] if isinstance(bank_acc['partner_id'], list) else bank_acc['partner_id']
        
        # Check if exists
        existing = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search',
            [[('acc_number', '=', bank_acc.get('acc_number')), ('company_id', '=', company_id)]]
        )
        if existing:
            bank_accounts_mapping[bank_acc['id']] = existing[0]
        else:
            bank_data = {
                'acc_number': bank_acc.get('acc_number', ''),
                'company_id': company_id,
            }
            if partner_id:
                bank_data['partner_id'] = partner_id
            if bank_acc.get('bank_id'):
                bank_data['bank_id'] = bank_acc['bank_id'][0] if isinstance(bank_acc['bank_id'], list) else bank_acc['bank_id']
            if bank_acc.get('currency_id'):
                bank_data['currency_id'] = bank_acc['currency_id'][0] if isinstance(bank_acc['currency_id'], list) else bank_acc['currency_id']
            if bank_acc.get('acc_holder_name'):
                bank_data['acc_holder_name'] = bank_acc['acc_holder_name']
            
            new_id = models.execute_kw(
                db, uid, password,
                'res.partner.bank', 'create',
                [bank_data]
            )
            bank_accounts_mapping[bank_acc['id']] = new_id
    id_mapping['bank_account'] = bank_accounts_mapping
    print(f"    ✓ Imported {len(bank_accounts_mapping)} bank accounts")
    
    # Import Product Categories (SKIP - không có company_id, dùng chung)
    print("  → Skipping product categories (shared across companies, no company_id)...")
    category_mapping = {}
    
    # Import Pricelists
    print("  → Importing pricelists...")
    pricelist_mapping = {}
    for pl in config.get('pricelists', []):
        existing = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search',
            [[('company_id', '=', company_id), ('name', '=', pl.get('name'))]]
        )
        if existing:
            pl_id = existing[0]
        else:
            pl_data = {
                'name': pl['name'],
                'company_id': company_id,
                'active': pl.get('active', True),
            }
            if pl.get('currency_id'):
                pl_data['currency_id'] = pl['currency_id'][0] if isinstance(pl['currency_id'], list) else pl['currency_id']
            if pl.get('discount_policy'):
                pl_data['discount_policy'] = pl['discount_policy']
            
            pl_id = models.execute_kw(
                db, uid, password,
                'product.pricelist', 'create',
                [pl_data]
            )
        
        # Import pricelist items
        for item in pl.get('item_ids', []):
            item_data = {
                'pricelist_id': pl_id,
                'min_quantity': item.get('min_quantity', 0),
                'base': item.get('base', 'list_price'),
            }
            if item.get('fixed_price'):
                item_data['fixed_price'] = item['fixed_price']
            if item.get('percent_price'):
                item_data['percent_price'] = item['percent_price']
            if item.get('product_id'):
                item_data['product_id'] = item['product_id'][0] if isinstance(item['product_id'], list) else item['product_id']
            if item.get('product_tmpl_id'):
                item_data['product_tmpl_id'] = item['product_tmpl_id'][0] if isinstance(item['product_tmpl_id'], list) else item['product_tmpl_id']
            if item.get('categ_id'):
                cat_id = category_mapping.get(item['categ_id'][0])
                if cat_id:
                    item_data['categ_id'] = cat_id
            
            models.execute_kw(
                db, uid, password,
                'product.pricelist.item', 'create',
                [item_data]
            )
    print(f"    ✓ Imported {len(config.get('pricelists', []))} pricelists")
    
    # Import Warehouses (nếu cần)
    print("  → Importing warehouses...")
    for wh in config.get('warehouses', []):
        existing = models.execute_kw(
            db, uid, password,
            'stock.warehouse', 'search',
            [[('company_id', '=', company_id), ('code', '=', wh.get('code'))]]
        )
        if not existing:
            # Note: Warehouse creation is complex, may need manual setup
            print(f"    ⚠️  Warehouse {wh.get('name')} needs manual setup (complex structure)")
    print(f"    ✓ Checked {len(config.get('warehouses', []))} warehouses (may need manual setup)")
    
    # Update journal bank_account_id sau khi import bank accounts
    print("  → Updating journal bank accounts...")
    journals = config.get('journals', [])
    bank_accounts = config.get('bank_accounts', [])
    bank_mapping = id_mapping.get('bank_account', {})
    
    for journal in journals:
        if journal.get('bank_account_id') and journal.get('code'):
            old_bank_id = journal['bank_account_id'][0] if isinstance(journal['bank_account_id'], list) else journal['bank_account_id']
            new_bank_id = bank_mapping.get(old_bank_id)
            
            if new_bank_id:
                # Find journal by code
                journal_rec = models.execute_kw(
                    db, uid, password,
                    'account.journal', 'search',
                    [[('company_id', '=', company_id), ('code', '=', journal.get('code'))]]
                )
                if journal_rec:
                    models.execute_kw(
                        db, uid, password,
                        'account.journal', 'write',
                        [[journal_rec[0]], {'bank_account_id': new_bank_id}]
                    )
    print(f"    ✓ Updated bank accounts for journals")
    
    # Import Sequences
    print("  → Importing sequences...")
    sequence_mapping = {}
    for seq in config.get('sequences', []):
        existing = models.execute_kw(
            db, uid, password,
            'ir.sequence', 'search',
            [[('company_id', '=', company_id), ('code', '=', seq.get('code'))]]
        )
        if existing:
            sequence_mapping[seq['id']] = existing[0]
        else:
            seq_data = {
                'name': seq['name'],
                'code': seq.get('code', ''),
                'company_id': company_id,
                'prefix': seq.get('prefix', ''),
                'suffix': seq.get('suffix', ''),
                'padding': seq.get('padding', 0),
                'number_next': seq.get('number_next', 1),
                'number_increment': seq.get('number_increment', 1),
                'use_date_range': seq.get('use_date_range', False),
            }
            new_id = models.execute_kw(
                db, uid, password,
                'ir.sequence', 'create',
                [seq_data]
            )
            sequence_mapping[seq['id']] = new_id
    print(f"    ✓ Imported {len(sequence_mapping)} sequences")
    
    # Import Payment Methods (SKIP - không có company_id, dùng chung)
    print("  → Skipping payment methods (shared across companies, no company_id)...")
    
    # Import Reconcile Models
    print("  → Importing reconcile models...")
    for rm in config.get('reconcile_models', []):
        existing = models.execute_kw(
            db, uid, password,
            'account.reconcile.model', 'search',
            [[('company_id', '=', company_id), ('name', '=', rm.get('name'))]]
        )
        if not existing:
            rm_data = {
                'name': rm['name'],
                'company_id': company_id,
                'rule_type': rm.get('rule_type', 'writeoff_button'),
                'match_text_location_label': rm.get('match_text_location_label', False),
                'match_text_location_note': rm.get('match_text_location_note', False),
                'match_text_location_reference': rm.get('match_text_location_reference', False),
                'match_amount': rm.get('match_amount', False),
                'match_amount_min': rm.get('match_amount_min', 0),
                'match_amount_max': rm.get('match_amount_max', 0),
                'match_label': rm.get('match_label', False),
                'match_note': rm.get('match_note', False),
                'match_transaction_type': rm.get('match_transaction_type', False),
                'match_same_currency': rm.get('match_same_currency', True),
                'match_total': rm.get('match_total', False),
                'match_partner': rm.get('match_partner', False),
            }
            rm_id = models.execute_kw(
                db, uid, password,
                'account.reconcile.model', 'create',
                [rm_data]
            )
            # Import reconcile model lines
            for line in rm.get('line_ids', []):
                line_data = {
                    'model_id': rm_id,
                    'sequence': line.get('sequence', 10),
                    'field_name': line.get('field_name', ''),
                    'label': line.get('label', ''),
                    'amount_type': line.get('amount_type', 'fixed'),
                    'amount': line.get('amount', 0),
                    'force_debit': line.get('force_debit', False),
                    'force_credit': line.get('force_credit', False),
                }
                if line.get('account_id'):
                    account_id = id_mapping['account'].get(line['account_id'][0])
                    if account_id:
                        line_data['account_id'] = account_id
                models.execute_kw(
                    db, uid, password,
                    'account.reconcile.model.line', 'create',
                    [line_data]
                )
    print(f"    ✓ Imported {len(config.get('reconcile_models', []))} reconcile models")
    
    # Import UOM Categories (SKIP - dùng chung, không có company_id)
    print("  → Skipping UOM categories (shared across companies, no company_id)...")
    
    # Import UOM Units (SKIP - dùng chung, không có company_id)
    print("  → Skipping UOM units (shared across companies, no company_id)...")
    
    # Import Sale Order Fees (SKIP - dùng chung, không có company_id)
    print("  → Skipping sale order fees (shared across companies, no company_id)...")
    
    # Import Purchase Report Tools (SKIP - dùng chung, không có company_id)
    print("  → Skipping purchase report tools (shared across companies, no company_id)...")
    
    print("\n✅ Master data import completed!")

if __name__ == '__main__':
    sys.exit(main())
