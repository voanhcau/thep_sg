#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Company Migration Script

Script này merge 3 scripts thành 1:
- export_accounting_config.py
- import_accounting_config.py
- export_import_translations.py

Cung cấp các commands:
  export accounting [env] [company_id] [output_file]
  export translations [env] [company_id] [output_file]
  export all [env] [company_id] [output_dir]
  import accounting [env] [config_file] [target_company_id] [target_company_name]
  import translations [env] [translations_file] [target_company_id]
  import all [env] [config_file] [translations_file] [target_company_id] [target_company_name]

Example:
  python migrate_company.py export all prod 1 ./migration_data
  python migrate_company.py import all prod ./migration_data/accounting_config_company_1_*.json ./migration_data/translations_company_1.json 2 "New Company"
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

# ============================================================================
# CONNECTION HELPERS
# ============================================================================

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

# ============================================================================
# EXPORT ACCOUNTING CONFIG (from export_accounting_config.py)
# ============================================================================

def export_accounting_config(models, uid, password, db, company_id):
    """Export tất cả cấu hình kế toán từ công ty nguồn"""
    
    config = {
        'export_date': datetime.now().isoformat(),
        'source_company_id': company_id,
        'export_version': '1.0',
        'company': {},
        'chart_of_accounts': [],
        'account_groups': [],
        'journals': [],
        'taxes': [],
        'tax_groups': [],
        'fiscal_positions': [],
        'payment_terms': [],
        'account_tags': [],
        'config_parameters': [],
        'bank_accounts': [],
        'sale_commission_rates': [],
        'sale_commission_configs': [],
        'pricelists': [],
        'warehouses': [],
        'sequences': [],
        'reconcile_models': [],
    }
    
    print(f"\n{'='*70}")
    print(f"📊 EXPORTING ACCOUNTING CONFIGURATION")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"Export Date: {config['export_date']}")
    print(f"{'='*70}\n")
    
    # 1. Export Company Info
    print("  [1/17] Exporting company information...")
    try:
        fields_to_export = [
            'name', 'vat', 'street', 'city', 'country_id', 'currency_id',
            'phone', 'email', 'website',
            'sale_description', 'purchase_description', 'signature',
            'signature_so', 'signature_po', 'interest_calculation_extra_days',
            'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
            'hide_report_footer',
        ]
        
        try:
            test_read = models.execute_kw(
                db, uid, password,
                'res.company', 'read',
                [[company_id]],
                {'fields': ['anglo_saxon_accounting']}
            )
            fields_to_export.insert(8, 'anglo_saxon_accounting')
        except:
            pass
        
        company = models.execute_kw(
            db, uid, password,
            'res.company', 'read',
            [[company_id]],
            {'fields': fields_to_export}
        )
        if company:
            config['company'] = company[0]
            print(f"    ✓ Company: {company[0].get('name', 'N/A')}")
        else:
            print(f"    ⚠️  Company ID {company_id} not found")
    except Exception as e:
        print(f"    ❌ Error exporting company: {str(e)[:100]}")
        return None
    
    # 2. Export Chart of Accounts
    print("  [2/17] Exporting chart of accounts...")
    try:
        accounts = models.execute_kw(
            db, uid, password,
            'account.account', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': [
                'code', 'name', 'account_type', 'deprecated', 'reconcile',
                'currency_id', 'group_id', 'tag_ids',
            ]}
        )
        config['chart_of_accounts'] = accounts
        print(f"    ✓ Exported {len(accounts)} accounts")
    except Exception as e:
        print(f"    ❌ Error exporting accounts: {str(e)[:100]}")
        config['chart_of_accounts'] = []
    
    # 3. Export Account Groups
    print("  [3/17] Exporting account groups...")
    try:
        account_groups = models.execute_kw(
            db, uid, password,
            'account.group', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['code_prefix_start', 'code_prefix_end', 'name', 'parent_id']}
        )
        config['account_groups'] = account_groups
        print(f"    ✓ Exported {len(account_groups)} account groups")
    except Exception as e:
        print(f"    ❌ Error exporting account groups: {str(e)[:100]}")
        config['account_groups'] = []
    
    # 4. Export Journals
    print("  [4/17] Exporting journals...")
    try:
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
    except Exception as e:
        print(f"    ❌ Error exporting journals: {str(e)[:100]}")
        config['journals'] = []
    
    # 5. Export Taxes
    print("  [5/17] Exporting taxes...")
    try:
        taxes = models.execute_kw(
            db, uid, password,
            'account.tax', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': [
                'name', 'description', 'amount', 'amount_type', 'type_tax_use',
                'tax_scope', 'active', 'sequence', 'tax_group_id',
                'price_include', 'include_base_amount', 'is_base_affected',
                'invoice_repartition_line_ids', 'refund_repartition_line_ids',
            ]}
        )
        for tax in taxes:
            if tax.get('invoice_repartition_line_ids'):
                try:
                    invoice_lines = models.execute_kw(
                        db, uid, password,
                        'account.tax.repartition.line', 'read',
                        [tax['invoice_repartition_line_ids']],
                        {'fields': ['repartition_type', 'account_id', 'factor_percent']}
                    )
                    tax['invoice_repartition_lines'] = invoice_lines
                except:
                    pass
            if tax.get('refund_repartition_line_ids'):
                try:
                    refund_lines = models.execute_kw(
                        db, uid, password,
                        'account.tax.repartition.line', 'read',
                        [tax['refund_repartition_line_ids']],
                        {'fields': ['repartition_type', 'account_id', 'factor_percent']}
                    )
                    tax['refund_repartition_lines'] = refund_lines
                except:
                    pass
        config['taxes'] = taxes
        print(f"    ✓ Exported {len(taxes)} taxes")
    except Exception as e:
        print(f"    ❌ Error exporting taxes: {str(e)[:100]}")
        config['taxes'] = []
    
    # 6. Export Tax Groups
    print("  [6/17] Exporting tax groups...")
    tax_group_ids = set()
    for tax in taxes:
        if tax.get('tax_group_id') and isinstance(tax['tax_group_id'], list) and len(tax['tax_group_id']) > 0:
            tax_group_ids.add(tax['tax_group_id'][0])
    
    tax_groups = []
    if tax_group_ids:
        tax_groups = models.execute_kw(
            db, uid, password,
            'account.tax.group', 'read',
            [list(tax_group_ids)],
            {'fields': ['name', 'sequence', 'preceding_subtotal']}
        )
    config['tax_groups'] = tax_groups
    print(f"    ✓ Exported {len(tax_groups)} tax groups")
    
    # 7. Export Fiscal Positions
    print("  [7/17] Exporting fiscal positions...")
    try:
        fiscal_positions = models.execute_kw(
            db, uid, password,
            'account.fiscal.position', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': [
                'name', 'active', 'country_id', 'country_group_id',
                'vat_required', 'auto_apply',
            ]}
        )
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
    except Exception as e:
        print(f"    ❌ Error exporting fiscal positions: {str(e)[:100]}")
        config['fiscal_positions'] = []
    
    # 8. Export Payment Terms
    print("  [8/17] Exporting payment terms...")
    try:
        payment_terms = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active', 'note']}
        )
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
    except Exception as e:
        print(f"    ❌ Error exporting payment terms: {str(e)[:100]}")
        config['payment_terms'] = []
    
    # 9. Export Account Tags
    print("  [9/17] Exporting account tags...")
    try:
        account_tags = models.execute_kw(
            db, uid, password,
            'account.account.tag', 'search_read',
            [[('applicability', '=', 'accounts')]],
            {'fields': ['name', 'color', 'active']}
        )
        config['account_tags'] = account_tags
        print(f"    ✓ Exported {len(account_tags)} account tags")
    except Exception as e:
        print(f"    ❌ Error exporting account tags: {str(e)[:100]}")
        config['account_tags'] = []
    
    # 10. Export Config Parameters
    print("  [10/17] Exporting config parameters...")
    try:
        config_params = models.execute_kw(
            db, uid, password,
            'ir.config_parameter', 'search_read',
            [[('key', 'like', 'nsgerp.%')]],
            {'fields': ['key', 'value']}
        )
        config['config_parameters'] = config_params
        print(f"    ✓ Exported {len(config_params)} config parameters")
    except Exception as e:
        print(f"    ❌ Error exporting config parameters: {str(e)[:100]}")
        config['config_parameters'] = []
    
    # 11. Export Bank Accounts
    print("  [11/17] Exporting bank accounts...")
    try:
        bank_accounts = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': [
                'acc_number', 'bank_id', 'partner_id', 'currency_id',
                'acc_holder_name', 'acc_type', 'sanitized_acc_number',
            ]}
        )
        config['bank_accounts'] = bank_accounts
        print(f"    ✓ Exported {len(bank_accounts)} bank accounts")
    except Exception as e:
        print(f"    ❌ Error exporting bank accounts: {str(e)[:100]}")
        config['bank_accounts'] = []
    
    # 12-17. Export other master data (simplified)
    print("  [12/17] Exporting sale commission rates...")
    try:
        sale_commission_rates = models.execute_kw(
            db, uid, password,
            'sale.commission.rate', 'search_read',
            [[]],
            {'fields': ['name', 'from_qty', 'to_qty', 'supplier_id', 'rate', 'type']}
        )
        config['sale_commission_rates'] = sale_commission_rates
        print(f"    ✓ Exported {len(sale_commission_rates)} sale commission rates")
    except:
        config['sale_commission_rates'] = []
    
    print("  [13/17] Exporting sale commission configs...")
    try:
        sale_commission_configs = models.execute_kw(
            db, uid, password,
            'sale.commission.config', 'search_read',
            [[]],
            {'fields': ['name', 'commission_tool_id']}
        )
        config['sale_commission_configs'] = sale_commission_configs
        print(f"    ✓ Exported {len(sale_commission_configs)} sale commission configs")
    except:
        config['sale_commission_configs'] = []
    
    print("  [14/17] Exporting pricelists...")
    try:
        pricelists = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active', 'currency_id', 'discount_policy']}
        )
        for pl in pricelists:
            pl_id = pl['id']
            items = models.execute_kw(
                db, uid, password,
                'product.pricelist.item', 'search_read',
                [[('pricelist_id', '=', pl_id)]],
                {'fields': ['product_id', 'product_tmpl_id', 'categ_id', 'min_quantity', 'fixed_price', 'percent_price', 'base']}
            )
            pl['item_ids'] = items
        config['pricelists'] = pricelists
        print(f"    ✓ Exported {len(pricelists)} pricelists")
    except:
        config['pricelists'] = []
    
    print("  [15/17] Exporting warehouses...")
    try:
        warehouses = models.execute_kw(
            db, uid, password,
            'stock.warehouse', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'code', 'active', 'partner_id', 'view_location_id', 'lot_stock_id']}
        )
        config['warehouses'] = warehouses
        print(f"    ✓ Exported {len(warehouses)} warehouses")
    except:
        config['warehouses'] = []
    
    print("  [16/17] Exporting sequences...")
    try:
        sequences = models.execute_kw(
            db, uid, password,
            'ir.sequence', 'search_read',
            [[('company_id', '=', company_id), '|', ('code', 'like', 'account.%'), ('code', 'like', 'journal.%')]],
            {'fields': ['name', 'code', 'prefix', 'suffix', 'padding', 'number_next', 'number_increment', 'use_date_range']}
        )
        config['sequences'] = sequences
        print(f"    ✓ Exported {len(sequences)} sequences")
    except:
        config['sequences'] = []
    
    print("  [17/17] Exporting reconcile models...")
    try:
        reconcile_models = models.execute_kw(
            db, uid, password,
            'account.reconcile.model', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'rule_type', 'match_text_location_label', 'match_text_location_note', 'match_text_location_reference', 'match_amount', 'match_amount_min', 'match_amount_max', 'match_label', 'match_note', 'match_transaction_type', 'match_same_currency', 'match_total', 'match_partner', 'line_ids']}
        )
        for rm in reconcile_models:
            rm_id = rm['id']
            lines = models.execute_kw(
                db, uid, password,
                'account.reconcile.model.line', 'search_read',
                [[('model_id', '=', rm_id)]],
                {'fields': ['sequence', 'field_name', 'label', 'amount_type', 'amount', 'force_debit', 'force_credit', 'account_id']}
            )
            rm['line_ids'] = lines
        config['reconcile_models'] = reconcile_models
        print(f"    ✓ Exported {len(reconcile_models)} reconcile models")
    except:
        config['reconcile_models'] = []
    
    return config

# ============================================================================
# EXPORT TRANSLATIONS (from export_import_translations.py)
# ============================================================================

def export_translations(models, uid, password, db, company_id):
    """Export translations từ company nguồn"""
    print(f"\n{'='*70}")
    print(f"📤 EXPORTING TRANSLATIONS")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    translations_data = {
        'export_date': datetime.now().isoformat(),
        'source_company_id': company_id,
        'translations': []
    }
    
    models_to_export = [
        {'model': 'account.account', 'fields': ['name'], 'key_field': 'code'},
        {'model': 'account.tax', 'fields': ['name', 'description'], 'key_field': 'name'},
        {'model': 'account.fiscal.position', 'fields': ['name'], 'key_field': 'name'},
        {'model': 'account.journal', 'fields': ['name'], 'key_field': 'code'},
        {'model': 'account.payment.term', 'fields': ['name'], 'key_field': 'name'},
        {'model': 'product.template', 'fields': ['name'], 'key_field': 'default_code'},
        {'model': 'product.category', 'fields': ['name'], 'key_field': 'name'},
    ]
    
    total_translations = 0
    
    for model_config in models_to_export:
        model_name = model_config['model']
        fields = model_config['fields']
        key_field = model_config['key_field']
        
        print(f"  → Exporting translations for {model_name}...")
        
        try:
            search_domain = []
            if model_name in ['account.account', 'account.tax', 'account.fiscal.position', 
                             'account.journal', 'account.payment.term']:
                search_domain = [('company_id', '=', company_id)]
            elif model_name in ['product.template', 'product.category']:
                search_domain = []
            
            records = models.execute_kw(
                db, uid, password,
                model_name, 'search_read',
                [search_domain],
                {'fields': ['id', key_field] + fields}
            )
            
            if not records:
                print(f"    ⏭️  No records found for {model_name}")
                continue
            
            print(f"    ✓ Found {len(records)} records")
            
            for record in records:
                record_id = record['id']
                key_value = record.get(key_field, '')
                
                for field in fields:
                    original_value = record.get(field, '')
                    if not original_value:
                        continue
                    
                    try:
                        langs = models.execute_kw(
                            db, uid, password,
                            'res.lang', 'search_read',
                            [[]],
                            {'fields': ['code', 'name']}
                        )
                    except:
                        langs = []
                    
                    for lang in langs:
                        lang_code = lang.get('code', '')
                        if not lang_code or lang_code == 'en_US':
                            continue
                        
                        try:
                            record_with_lang = models.execute_kw(
                                db, uid, password,
                                model_name, 'read',
                                [[record_id]],
                                {'fields': [field], 'context': {'lang': lang_code}}
                            )
                            
                            if record_with_lang and record_with_lang[0].get(field):
                                translated_value = record_with_lang[0][field]
                                
                                if translated_value and translated_value != original_value:
                                    translations_data['translations'].append({
                                        'model': model_name,
                                        'field': field,
                                        'res_id': record_id,
                                        'key_value': key_value,
                                        'lang': lang_code,
                                        'value': translated_value,
                                        'src': original_value,
                                    })
                                    total_translations += 1
                        except:
                            continue
            
            model_trans_count = len([t for t in translations_data['translations'] if t['model'] == model_name])
            print(f"    ✓ Exported {model_trans_count} translations")
            
        except Exception as e:
            print(f"    ⚠️  Error exporting {model_name}: {str(e)[:100]}")
    
    print(f"\n{'='*70}")
    print(f"✅ EXPORT COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Total translations exported: {total_translations}")
    print(f"{'='*70}\n")
    
    return translations_data

# ============================================================================
# IMPORT ACCOUNTING CONFIG (from import_accounting_config.py)
# ============================================================================

def load_config(config_file):
    """Load configuration từ JSON file"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_or_get_company(models, uid, password, db, company_data, target_company_id=None, target_company_name=None):
    """Tạo hoặc lấy company"""
    if target_company_id:
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
    
    company_name = target_company_name or company_data.get('name', 'New Company')
    
    existing = models.execute_kw(
        db, uid, password,
        'res.company', 'search',
        [[('name', '=', company_name)]]
    )
    if existing:
        print(f"✅ Company already exists: {company_name} (ID: {existing[0]})")
        return existing[0]
    
    new_company_data = {
        'name': company_name,
        'currency_id': company_data.get('currency_id', [1])[0] if isinstance(company_data.get('currency_id'), list) else company_data.get('currency_id', 1),
        'country_id': company_data.get('country_id', [241])[0] if isinstance(company_data.get('country_id'), list) else company_data.get('country_id', 241),
    }
    
    company_id = models.execute_kw(
        db, uid, password,
        'res.company', 'create',
        [new_company_data]
    )
    
    print(f"✅ Created new company: {company_name} (ID: {company_id})")
    return company_id

# Import functions (simplified - full implementation from import_accounting_config.py)
def import_chart_of_accounts(models, uid, password, db, accounts, account_groups, company_id, id_mapping):
    """Import chart of accounts"""
    print("\n📊 [1/8] Importing Chart of Accounts...")
    
    group_mapping = {}
    if account_groups:
        groups_sorted = sorted(account_groups, key=lambda x: (x.get('parent_id', [False])[0] if isinstance(x.get('parent_id'), list) else x.get('parent_id', False), x.get('id', 0)))
        
        for group in groups_sorted:
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
    
    accounts_sorted = sorted(accounts, key=lambda x: x.get('code', ''))
    
    for account in accounts_sorted:
        existing = models.execute_kw(
            db, uid, password,
            'account.account', 'search',
            [[('company_id', '=', company_id), ('code', '=', account.get('code'))]]
        )
        if existing:
            id_mapping['account'][account['id']] = existing[0]
            continue
        
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
    print("\n💰 [3/8] Importing Taxes...")
    
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
        
        new_id = models.execute_kw(
            db, uid, password,
            'account.tax', 'create',
            [tax_data]
        )
        id_mapping['tax'][tax['id']] = new_id
    
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
        pt_company_id = pt.get('company_id')
        if isinstance(pt_company_id, list):
            pt_company_id = pt_company_id[0]
        
        if not pt_company_id or pt_company_id == company_id:
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
                    'company_id': company_id,
                    'active': pt.get('active', True),
                    'note': pt.get('note', ''),
                }
                pt_id = models.execute_kw(
                    db, uid, password,
                    'account.payment.term', 'create',
                    [pt_data]
                )
            
            payment_terms_mapping[pt['id']] = pt_id
            
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
    
    if 'anglo_saxon_accounting' in company_data:
        anglo_saxon = company_data.get('anglo_saxon_accounting')
        if anglo_saxon is not None:
            try:
                test_read = models.execute_kw(
                    db, uid, password,
                    'res.company', 'read',
                    [[company_id]],
                    {'fields': ['anglo_saxon_accounting']}
                )
                update_data['anglo_saxon_accounting'] = bool(anglo_saxon)
                print(f"   → Anglo-saxon accounting: {'Enabled' if anglo_saxon else 'Disabled'}")
            except:
                pass
    
    custom_fields = [
        'sale_description', 'purchase_description', 'signature',
        'signature_so', 'signature_po', 'interest_calculation_extra_days',
        'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
        'hide_report_footer',
    ]
    
    for field in custom_fields:
        if field in company_data:
            value = company_data[field]
            if value is None:
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            if isinstance(value, str) and value == '':
                continue
            if field in ['signature_so', 'signature_po', 'hide_report_footer']:
                update_data[field] = bool(value)
            elif field == 'signature' and (value is False or value == ''):
                continue
            else:
                update_data[field] = value
    
    clean_data = {}
    for k, v in update_data.items():
        if v is None:
            continue
        if isinstance(v, str) and 'None' in v:
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
            print(f"   ⚠️  Warning: Could not update company settings: {str(e)[:200]}")

def import_config_parameters(models, uid, password, db, config_params):
    """Import config parameters"""
    print("\n🔧 [7/8] Importing Config Parameters...")
    
    for param in config_params:
        existing = models.execute_kw(
            db, uid, password,
            'ir.config_parameter', 'search',
            [[('key', '=', param.get('key'))]]
        )
        if existing:
            models.execute_kw(
                db, uid, password,
                'ir.config_parameter', 'write',
                [[existing[0]], {'value': param.get('value', '')}]
            )
        else:
            models.execute_kw(
                db, uid, password,
                'ir.config_parameter', 'create',
                [{
                    'key': param.get('key'),
                    'value': param.get('value', ''),
                }]
            )
    
    print(f"   ✓ Imported {len(config_params)} config parameters")

def import_master_data(models, uid, password, db, config, company_id, id_mapping):
    """Import master data từ ngs_sale module"""
    print("\n📦 [8/8] Importing Master Data from ngs_sale...")
    
    # Import Bank Accounts
    print("  → Importing bank accounts...")
    bank_accounts_mapping = {}
    for bank_acc in config.get('bank_accounts', []):
        partner_id = None
        if bank_acc.get('partner_id'):
            partner_id = bank_acc['partner_id'][0] if isinstance(bank_acc['partner_id'], list) else bank_acc['partner_id']
        
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
    
    print("\n✅ Master data import completed!")

def import_accounting_config(models, uid, password, db, config, target_company_id=None, target_company_name=None):
    """Import accounting configuration"""
    print(f"\n{'='*70}")
    print(f"📥 IMPORTING ACCOUNTING CONFIGURATION")
    print(f"{'='*70}")
    print(f"Target company ID: {target_company_id if target_company_id else 'New (will be created)'}")
    print(f"Target company name: {target_company_name or 'N/A'}")
    print(f"{'='*70}\n")
    
    id_mapping = {
        'account': {},
        'journal': {},
        'tax': {},
        'tax_group': {},
    }
    
    company_id = create_or_get_company(
        models, uid, password, db,
        config['company'],
        target_company_id,
        target_company_name
    )
    
    if not company_id:
        print("❌ Failed to create/get company")
        return None
    
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
    
    print(f"\n{'='*70}")
    print(f"✅ IMPORT COMPLETED")
    print(f"{'='*70}")
    
    return company_id

# ============================================================================
# IMPORT TRANSLATIONS (from export_import_translations.py)
# ============================================================================

def import_translations(models, uid, password, db, import_data, target_company_id):
    """Import translations vào company đích"""
    print(f"\n{'='*70}")
    print(f"📥 IMPORTING TRANSLATIONS")
    print(f"{'='*70}")
    print(f"Target Company ID: {target_company_id}")
    print(f"Source Company ID: {import_data.get('source_company_id', 'N/A')}")
    print(f"⚠️  MODE: UPDATE translations if they exist (will overwrite existing translations)")
    print(f"{'='*70}\n")
    
    translations_by_model = defaultdict(list)
    for trans in import_data.get('translations', []):
        translations_by_model[trans['model']].append(trans)
    
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for model_name, translations in translations_by_model.items():
        print(f"  → Processing {model_name}...")
        
        key_field_map = {
            'account.account': 'code',
            'account.tax': 'name',
            'account.fiscal.position': 'name',
            'account.journal': 'code',
            'account.payment.term': 'name',
            'product.template': 'default_code',
            'product.category': 'name',
        }
        
        key_field = key_field_map.get(model_name, 'name')
        
        print(f"    → Building {key_field} → res_id mapping...")
        
        try:
            search_domain = []
            if model_name in ['account.account', 'account.tax', 'account.fiscal.position', 
                             'account.journal', 'account.payment.term']:
                search_domain = [('company_id', '=', target_company_id)]
            elif model_name in ['product.template', 'product.category']:
                search_domain = []
            
            target_records = models.execute_kw(
                db, uid, password,
                model_name, 'search_read',
                [search_domain],
                {'fields': ['id', key_field]}
            )
            
            key_to_id = {}
            for record in target_records:
                key_value = record.get(key_field, '')
                if key_value:
                    key_to_id[key_value] = record['id']
            
            print(f"    ✓ Mapped {len(key_to_id)} records")
            
        except Exception as e:
            print(f"    ⚠️  Error getting target records: {str(e)[:100]}")
            continue
        
        print(f"    → Importing {len(translations)} translations...")
        
        for trans in translations:
            key_value = trans.get('key_value', '')
            target_res_id = key_to_id.get(key_value)
            
            if not target_res_id:
                skipped_count += 1
                continue
            
            try:
                models.execute_kw(
                    db, uid, password,
                    model_name, 'write',
                    [[target_res_id], {
                        trans['field']: trans['value']
                    }],
                    {'context': {'lang': trans['lang']}}
                )
                success_count += 1
                if success_count <= 20:
                    print(f"      ✓ Set {trans['lang']} translation for {key_value}")
            except Exception as e:
                error_count += 1
                print(f"      ⚠️  Error setting translation: {str(e)[:80]}")
        
        print(f"    ✓ Completed: {len(translations)} translations processed")
    
    print(f"\n{'='*70}")
    print(f"✅ IMPORT COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Results:")
    print(f"   ✓ Success (created/updated): {success_count}")
    print(f"   ⏭️  Skipped (record not found): {skipped_count}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"{'='*70}\n")
    
    return {
        'success': success_count,
        'skipped': skipped_count,
        'errors': error_count
    }

# ============================================================================
# SETUP CONTACTS (Task 1: Payment Terms & Pricelist)
# ============================================================================

def setup_contacts(models, uid, password, db, company_id):
    """
    Set Payment Terms và Pricelist cho tất cả contacts trong company
    - Payment Terms: "Thanh toán ngay"
    - Pricelist: "[Bán] Mặc định (VND)"
    - Chỉ set nếu chưa có giá trị (no override)
    """
    print(f"\n{'='*70}")
    print(f"👥 SETTING UP CONTACTS")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"{'='*70}\n")
    
    # Tìm Payment Term "Thanh toán ngay"
    print("  → Finding Payment Term 'Thanh toán ngay'...")
    payment_term_ids = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search',
        [[('name', '=', 'Thanh toán ngay')]]
    )
    if not payment_term_ids:
        print("    ❌ Payment Term 'Thanh toán ngay' not found")
        return False
    payment_term_id = payment_term_ids[0]
    print(f"    ✓ Found Payment Term ID: {payment_term_id}")
    
    # Tìm Pricelist "[Bán] Mặc định (VND)"
    print("  → Finding Pricelist '[Bán] Mặc định (VND)'...")
    pricelist_ids = models.execute_kw(
        db, uid, password,
        'product.pricelist', 'search',
        [[('name', '=', '[Bán] Mặc định (VND)')]]
    )
    if not pricelist_ids:
        print("    ❌ Pricelist '[Bán] Mặc định (VND)' not found")
        return False
    pricelist_id = pricelist_ids[0]
    print(f"    ✓ Found Pricelist ID: {pricelist_id}")
    
    # Lấy tất cả contacts (có thể filter theo company nếu cần)
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
    for contact_id in contact_ids:
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
            # Đã đọc với context company ở trên
            current_pricelist = contact_data.get('property_product_pricelist')
            if not current_pricelist or (isinstance(current_pricelist, list) and len(current_pricelist) == 0):
                # Set property field với context company
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
            error_count += 1
            if error_count <= 10:  # Log 10 errors đầu tiên
                print(f"    ⚠️  Error processing contact {contact_id}: {str(e)[:80]}")
    
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

# ============================================================================
# SETUP PRODUCTS (Task 2: Sales Tax for Stockable Products)
# ============================================================================

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
    
    # Tìm Tax "Thuế GTGT phải nộp 10% x"
    print("  → Finding Tax 'Thuế GTGT phải nộp 10% x'...")
    tax_ids = models.execute_kw(
        db, uid, password,
        'account.tax', 'search',
        [[('company_id', '=', company_id), ('name', '=', 'Thuế GTGT phải nộp 10% x')]]
    )
    if not tax_ids:
        print("    ❌ Tax 'Thuế GTGT phải nộp 10% x' not found for this company")
        return False
    tax_id = tax_ids[0]
    print(f"    ✓ Found Tax ID: {tax_id}")
    
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
    for product_id in product_ids:
        try:
            # Đọc product với context company để check property_account_income_id
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
                    print(f"      ✓ Set tax for: {product_data.get('name', 'N/A')}")
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
                        print(f"      ✓ Added tax for: {product_data.get('name', 'N/A')}")
                else:
                    skipped_count += 1
        
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Log 10 errors đầu tiên
                print(f"    ⚠️  Error processing product {product_id}: {str(e)[:80]}")
    
    print(f"\n{'='*70}")
    print(f"✅ SETUP COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Results:")
    print(f"   ✓ Updated products: {updated_count}")
    print(f"   ⏭️  Skipped products (already set): {skipped_count}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"{'='*70}\n")
    
    return True

# ============================================================================
# MAIN COMMAND HANDLER
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("\nExport commands:")
        print("  python migrate_company.py export accounting [env] [company_id] [output_file]")
        print("  python migrate_company.py export translations [env] [company_id] [output_file]")
        print("  python migrate_company.py export all [env] [company_id] [output_dir]")
        print("\nImport commands:")
        print("  python migrate_company.py import accounting [env] [config_file] [target_company_id] [target_company_name]")
        print("  python migrate_company.py import translations [env] [translations_file] [target_company_id]")
        print("  python migrate_company.py import all [env] [config_file] [translations_file] [target_company_id] [target_company_name]")
        print("\nSetup commands:")
        print("  python migrate_company.py setup contacts [env] [company_id]")
        print("  python migrate_company.py setup products [env] [company_id]")
        print("\nExample:")
        print("  python migrate_company.py export all prod 1 ./migration_data")
        print("  python migrate_company.py import all prod ./migration_data/accounting_config_company_1_*.json ./migration_data/translations_company_1.json 2 'New Company'")
        print("  python migrate_company.py setup contacts prod 2")
        print("  python migrate_company.py setup products prod 2")
        print("="*70)
        return 1
    
    action = sys.argv[1].lower()
    subaction = sys.argv[2].lower() if len(sys.argv) > 2 else None
    
    if action == 'export':
        if subaction == 'accounting':
            if len(sys.argv) < 6:
                print("❌ Missing arguments")
                print("Usage: export accounting [env] [company_id] [output_file]")
                return 1
            
            env_type = sys.argv[3]
            company_id = int(sys.argv[4])
            output_file = Path(sys.argv[5])
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            config = export_accounting_config(models, uid, password, db, company_id)
            if config:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False, default=str)
                print(f"\n✅ Export completed: {output_file}")
                return 0
            return 1
        
        elif subaction == 'translations':
            if len(sys.argv) < 6:
                print("❌ Missing arguments")
                print("Usage: export translations [env] [company_id] [output_file]")
                return 1
            
            env_type = sys.argv[3]
            company_id = int(sys.argv[4])
            output_file = Path(sys.argv[5])
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            translations_data = export_translations(models, uid, password, db, company_id)
            if translations_data:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(translations_data, f, indent=2, ensure_ascii=False, default=str)
                print(f"\n✅ Export completed: {output_file}")
                return 0
            return 1
        
        elif subaction == 'all':
            if len(sys.argv) < 6:
                print("❌ Missing arguments")
                print("Usage: export all [env] [company_id] [output_dir]")
                return 1
            
            env_type = sys.argv[3]
            company_id = int(sys.argv[4])
            output_dir = Path(sys.argv[5])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            # Export accounting
            config = export_accounting_config(models, uid, password, db, company_id)
            if config:
                accounting_file = output_dir / f'accounting_config_company_{company_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(accounting_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False, default=str)
                print(f"\n✅ Accounting export completed: {accounting_file}")
            
            # Export translations
            translations_data = export_translations(models, uid, password, db, company_id)
            if translations_data:
                translations_file = output_dir / f'translations_company_{company_id}.json'
                with open(translations_file, 'w', encoding='utf-8') as f:
                    json.dump(translations_data, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Translations export completed: {translations_file}")
            
            return 0
        
        else:
            print(f"❌ Unknown export subcommand: {subaction}")
            return 1
    
    elif action == 'import':
        if subaction == 'accounting':
            if len(sys.argv) < 6:
                print("❌ Missing arguments")
                print("Usage: import accounting [env] [config_file] [target_company_id] [target_company_name]")
                return 1
            
            env_type = sys.argv[3]
            config_file = Path(sys.argv[4])
            target_company_id = None if sys.argv[5].lower() in ['none', 'null', ''] else int(sys.argv[5])
            target_company_name = sys.argv[6] if len(sys.argv) > 6 else None
            
            if not config_file.exists():
                print(f"❌ Config file not found: {config_file}")
                return 1
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            config = load_config(config_file)
            company_id = import_accounting_config(models, uid, password, db, config, target_company_id, target_company_name)
            
            if company_id:
                print(f"\n✅ Import completed for company ID: {company_id}")
                return 0
            return 1
        
        elif subaction == 'translations':
            if len(sys.argv) < 6:
                print("❌ Missing arguments")
                print("Usage: import translations [env] [translations_file] [target_company_id]")
                return 1
            
            env_type = sys.argv[3]
            translations_file = Path(sys.argv[4])
            target_company_id = int(sys.argv[5])
            
            if not translations_file.exists():
                print(f"❌ Translations file not found: {translations_file}")
                return 1
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            with open(translations_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            result = import_translations(models, uid, password, db, import_data, target_company_id)
            print(f"\n✅ Import completed")
            return 0
        
        elif subaction == 'all':
            if len(sys.argv) < 7:
                print("❌ Missing arguments")
                print("Usage: import all [env] [config_file] [translations_file] [target_company_id] [target_company_name]")
                return 1
            
            env_type = sys.argv[3]
            config_file = Path(sys.argv[4])
            translations_file = Path(sys.argv[5])
            target_company_id = None if sys.argv[6].lower() in ['none', 'null', ''] else int(sys.argv[6])
            target_company_name = sys.argv[7] if len(sys.argv) > 7 else None
            
            if not config_file.exists():
                print(f"❌ Config file not found: {config_file}")
                return 1
            if not translations_file.exists():
                print(f"❌ Translations file not found: {translations_file}")
                return 1
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            # Import accounting first
            config = load_config(config_file)
            company_id = import_accounting_config(models, uid, password, db, config, target_company_id, target_company_name)
            
            if not company_id:
                print("❌ Failed to import accounting config")
                return 1
            
            # Import translations
            with open(translations_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            result = import_translations(models, uid, password, db, import_data, company_id)
            print(f"\n✅ All imports completed for company ID: {company_id}")
            return 0
        
        else:
            print(f"❌ Unknown import subcommand: {subaction}")
            return 1
    
    elif action == 'setup':
        if subaction == 'contacts':
            if len(sys.argv) < 5:
                print("❌ Missing arguments")
                print("Usage: setup contacts [env] [company_id]")
                return 1
            
            env_type = sys.argv[3]
            company_id = int(sys.argv[4])
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            result = setup_contacts(models, uid, password, db, company_id)
            return 0 if result else 1
        
        elif subaction == 'products':
            if len(sys.argv) < 5:
                print("❌ Missing arguments")
                print("Usage: setup products [env] [company_id]")
                return 1
            
            env_type = sys.argv[3]
            company_id = int(sys.argv[4])
            
            print(f"🔗 Connecting to {env_type} environment...")
            url, db, username, password, models, uid = get_connection(env_type)
            print(f"✅ Connected to {url} (DB: {db})")
            
            result = setup_products(models, uid, password, db, company_id)
            return 0 if result else 1
        
        else:
            print(f"❌ Unknown setup subcommand: {subaction}")
            print("Use 'contacts' or 'products'")
            return 1
    
    else:
        print(f"❌ Unknown action: {action}")
        print("Use 'export', 'import', or 'setup'")
        return 1

if __name__ == '__main__':
    sys.exit(main())
