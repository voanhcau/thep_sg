#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Accounting Configuration từ công ty hiện tại

Script này export tất cả cấu hình kế toán từ công ty nguồn để có thể import vào công ty mới.

Usage:
    python export_accounting_config.py [local|staging|prod] [source_company_id]
    
Example:
    python export_accounting_config.py local 1
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

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

def export_accounting_config(models, uid, password, db, company_id):
    """Export tất cả cấu hình kế toán"""
    
    config = {
        'export_date': datetime.now().isoformat(),
        'source_company_id': company_id,
        'company': {},
        'chart_of_accounts': [],
        'journals': [],
        'taxes': [],
        'tax_groups': [],
        'fiscal_positions': [],
        'payment_terms': [],
        'account_tags': [],
        'config_parameters': [],
    }
    
    print(f"📊 Exporting accounting configuration for company ID: {company_id}")
    
    # 1. Export Company Info
    print("  → Exporting company information...")
    company = models.execute_kw(
        db, uid, password,
        'res.company', 'read',
        [[company_id]],
        {'fields': [
            'name', 'vat', 'street', 'city', 'country_id', 'currency_id',
            'phone', 'email', 'website',
            'sale_description', 'purchase_description', 'signature',
            'signature_so', 'signature_po', 'interest_calculation_extra_days',
            'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
            'hide_report_footer',
        ]}
    )
    if company:
        config['company'] = company[0]
    
    # 2. Export Chart of Accounts
    print("  → Exporting chart of accounts...")
    accounts = models.execute_kw(
        db, uid, password,
        'account.account', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': [
            'code', 'name', 'account_type', 'deprecated', 'reconcile',
            'currency_id', 'group_id', 'tag_ids', 'deprecated',
        ]}
    )
    config['chart_of_accounts'] = accounts
    print(f"    ✓ Exported {len(accounts)} accounts")
    
    # 3. Export Account Groups
    print("  → Exporting account groups...")
    account_groups = models.execute_kw(
        db, uid, password,
        'account.group', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': ['code_prefix_start', 'code_prefix_end', 'name', 'parent_id']}
    )
    config['account_groups'] = account_groups
    print(f"    ✓ Exported {len(account_groups)} account groups")
    
    # 4. Export Journals
    print("  → Exporting journals...")
    journals = models.execute_kw(
        db, uid, password,
        'account.journal', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': [
            'name', 'code', 'type', 'default_account_id', 'currency_id',
            'bank_account_id', 'sequence', 'active',
        ]}
    )
    config['journals'] = journals
    print(f"    ✓ Exported {len(journals)} journals")
    
    # 5. Export Taxes
    print("  → Exporting taxes...")
    taxes = models.execute_kw(
        db, uid, password,
        'account.tax', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': [
            'name', 'description', 'amount', 'amount_type', 'type_tax_use',
            'tax_scope', 'active', 'sequence', 'tax_group_id',
            'account_id', 'refund_account_id', 'price_include',
            'include_base_amount', 'is_base_affected',
        ]}
    )
    config['taxes'] = taxes
    print(f"    ✓ Exported {len(taxes)} taxes")
    
    # 6. Export Tax Groups
    print("  → Exporting tax groups...")
    tax_groups = models.execute_kw(
        db, uid, password,
        'account.tax.group', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': ['name', 'sequence', 'preceding_subtotal']}
    )
    config['tax_groups'] = tax_groups
    print(f"    ✓ Exported {len(tax_groups)} tax groups")
    
    # 7. Export Fiscal Positions
    print("  → Exporting fiscal positions...")
    fiscal_positions = models.execute_kw(
        db, uid, password,
        'account.fiscal.position', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': [
            'name', 'active', 'country_id', 'country_group_id',
            'vat_required', 'auto_apply',
        ]}
    )
    # Export tax mappings
    for fp in fiscal_positions:
        fp_id = fp['id']
        tax_mappings = models.execute_kw(
            db, uid, password,
            'account.fiscal.position.tax', 'search_read',
            [[('position_id', '=', fp_id)]],
            {'fields': ['tax_src_id', 'tax_dest_id']}
        )
        fp['tax_ids'] = tax_mappings
        
        account_mappings = models.execute_kw(
            db, uid, password,
            'account.fiscal.position.account', 'search_read',
            [[('position_id', '=', fp_id)]],
            {'fields': ['account_src_id', 'account_dest_id']}
        )
        fp['account_ids'] = account_mappings
    
    config['fiscal_positions'] = fiscal_positions
    print(f"    ✓ Exported {len(fiscal_positions)} fiscal positions")
    
    # 8. Export Payment Terms
    print("  → Exporting payment terms...")
    payment_terms = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': ['name', 'active', 'note']}
    )
    # Export payment term lines
    for pt in payment_terms:
        pt_id = pt['id']
        lines = models.execute_kw(
            db, uid, password,
            'account.payment.term.line', 'search_read',
            [[('payment_id', '=', pt_id)]],
            {'fields': ['value', 'value_amount', 'nb_days', 'option', 'days_after']}
        )
        pt['line_ids'] = lines
    
    config['payment_terms'] = payment_terms
    print(f"    ✓ Exported {len(payment_terms)} payment terms")
    
    # 9. Export Account Tags
    print("  → Exporting account tags...")
    account_tags = models.execute_kw(
        db, uid, password,
        'account.account.tag', 'search_read',
        [[('applicability', '=', 'accounts')]],
        {'fields': ['name', 'color', 'active']}
    )
    config['account_tags'] = account_tags
    print(f"    ✓ Exported {len(account_tags)} account tags")
    
    # 10. Export Config Parameters (company-specific)
    print("  → Exporting config parameters...")
    config_params = models.execute_kw(
        db, uid, password,
        'ir.config_parameter', 'search_read',
        [[('key', 'like', 'nsgerp.%')]],
        {'fields': ['key', 'value']}
    )
    config['config_parameters'] = config_params
    print(f"    ✓ Exported {len(config_params)} config parameters")
    
    return config

def main():
    env_type = sys.argv[1] if len(sys.argv) > 1 else 'local'
    company_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"🔗 Connecting to {env_type} environment...")
    url, db, username, password, models, uid = get_connection(env_type)
    print(f"✅ Connected to {url} (DB: {db})")
    
    # Export configuration
    config = export_accounting_config(models, uid, password, db, company_id)
    
    # Save to JSON file
    output_file = Path(__file__).parent / f'accounting_config_company_{company_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Configuration exported to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Company: {config['company'].get('name', 'N/A')}")
    print(f"   - Accounts: {len(config['chart_of_accounts'])}")
    print(f"   - Journals: {len(config['journals'])}")
    print(f"   - Taxes: {len(config['taxes'])}")
    print(f"   - Fiscal Positions: {len(config['fiscal_positions'])}")
    print(f"   - Payment Terms: {len(config['payment_terms'])}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
