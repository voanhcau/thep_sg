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
        url = os.getenv("ODOO_URL", "http://localhost:6069")
        db = os.getenv("ODOO_DB", "16.thepnamsaigon.03.11.2025")
        username = os.getenv("ODOO_USERNAME", "nsgit")
        password = os.getenv("ODOO_PASSWORD", "1")
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
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
    print("\n📊 Importing Chart of Accounts...")
    
    # Import account groups first
    group_mapping = {}
    for group in account_groups:
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
    print("\n📝 Importing Journals...")
    
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
    print("\n💰 Importing Taxes...")
    
    # Import tax groups first
    for tax_group in tax_groups:
        existing = models.execute_kw(
            db, uid, password,
            'account.tax.group', 'search',
            [[('company_id', '=', company_id), ('name', '=', tax_group.get('name'))]]
        )
        if existing:
            id_mapping['tax_group'][tax_group['id']] = existing[0]
        else:
            tax_group_data = {
                'name': tax_group['name'],
                'company_id': company_id,
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
        
        if tax.get('account_id'):
            account_id = id_mapping['account'].get(tax['account_id'][0])
            if account_id:
                tax_data['account_id'] = account_id
        
        if tax.get('refund_account_id'):
            account_id = id_mapping['account'].get(tax['refund_account_id'][0])
            if account_id:
                tax_data['refund_account_id'] = account_id
        
        new_id = models.execute_kw(
            db, uid, password,
            'account.tax', 'create',
            [tax_data]
        )
        id_mapping['tax'][tax['id']] = new_id
    
    print(f"   ✓ Imported {len(taxes)} taxes")

def import_fiscal_positions(models, uid, password, db, fiscal_positions, company_id, id_mapping):
    """Import fiscal positions"""
    print("\n🌍 Importing Fiscal Positions...")
    
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
    print("\n💳 Importing Payment Terms...")
    
    for pt in payment_terms:
        existing = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search',
            [[('company_id', '=', company_id), ('name', '=', pt.get('name'))]]
        )
        if existing:
            pt_id = existing[0]
        else:
            pt_data = {
                'name': pt['name'],
                'company_id': company_id,
                'active': pt.get('active', True),
                'note': pt.get('note', ''),
            }
            pt_id = models.execute_kw(
                db, uid, password,
                'account.payment.term', 'create',
                [pt_data]
            )
        
        # Import payment term lines
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
    
    print(f"   ✓ Imported {len(payment_terms)} payment terms")

def import_company_settings(models, uid, password, db, company_data, company_id):
    """Import company custom settings"""
    print("\n⚙️  Importing Company Settings...")
    
    update_data = {}
    
    # Custom fields from ngs_sale
    custom_fields = [
        'sale_description', 'purchase_description', 'signature',
        'signature_so', 'signature_po', 'interest_calculation_extra_days',
        'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
        'hide_report_footer',
    ]
    
    for field in custom_fields:
        if field in company_data:
            update_data[field] = company_data[field]
    
    if update_data:
        models.execute_kw(
            db, uid, password,
            'res.company', 'write',
            [[company_id], update_data]
        )
        print(f"   ✓ Updated {len(update_data)} company settings")

def import_config_parameters(models, uid, password, db, config_params):
    """Import config parameters"""
    print("\n🔧 Importing Config Parameters...")
    
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

def main():
    if len(sys.argv) < 3:
        print("Usage: python import_accounting_config.py [env] [config_file.json] [target_company_id] [target_company_name]")
        print("Example: python import_accounting_config.py local config.json 2 'Công Ty Mới'")
        return 1
    
    env_type = sys.argv[1]
    config_file = Path(sys.argv[2])
    target_company_id = int(sys.argv[3]) if len(sys.argv) > 3 else None
    target_company_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return 1
    
    print(f"🔗 Connecting to {env_type} environment...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})")
    
    # Load config
    print(f"\n📂 Loading configuration from {config_file}...")
    config = load_config(config_file)
    
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
    
    print("\n✅ Import completed successfully!")
    print(f"\n📊 Summary:")
    print(f"   - Company ID: {company_id}")
    print(f"   - Accounts: {len(id_mapping['account'])}")
    print(f"   - Journals: {len(id_mapping['journal'])}")
    print(f"   - Taxes: {len(id_mapping['tax'])}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
