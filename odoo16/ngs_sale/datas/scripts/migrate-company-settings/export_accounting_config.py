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

def export_accounting_config(models, uid, password, db, company_id):
    """
    Export tất cả cấu hình kế toán từ công ty nguồn
    
    Best Practices:
    - Export chỉ các bảng có company_id (company-specific)
    - Skip các bảng dùng chung (không có company_id)
    - Handle errors gracefully với try-except
    - Provide clear progress indicators
    """
    
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
        'partner_types': [],
        'supplier_delivery_types': [],
        'sale_processing_states': [],
        'sale_commission_rates': [],
        'sale_commission_configs': [],
        'sale_barems': [],
        'product_categories': [],
        'pricelists': [],
        'warehouses': [],
        'sequences': [],
        'payment_methods': [],
        'reconcile_models': [],
        'uom_categories': [],
        'uom_units': [],
        'sale_order_fees': [],
        'purchase_report_tools': [],
    }
    
    print(f"\n{'='*70}")
    print(f"📊 EXPORTING ACCOUNTING CONFIGURATION")
    print(f"{'='*70}")
    print(f"Company ID: {company_id}")
    print(f"Export Date: {config['export_date']}")
    print(f"{'='*70}\n")
    
    # 1. Export Company Info
    print("  [1/23] Exporting company information...")
    try:
        # Try to export anglo_saxon_accounting (requires account_anglo_saxon module)
        fields_to_export = [
            'name', 'vat', 'street', 'city', 'country_id', 'currency_id',
            'phone', 'email', 'website',
            'sale_description', 'purchase_description', 'signature',
            'signature_so', 'signature_po', 'interest_calculation_extra_days',
            'delivery_receipt_construction_site', 'delivery_receipt_footer_notes',
            'hide_report_footer',
        ]
        
        # Try to add anglo_saxon_accounting field
        try:
            test_read = models.execute_kw(
                db, uid, password,
                'res.company', 'read',
                [[company_id]],
                {'fields': ['anglo_saxon_accounting']}
            )
            fields_to_export.insert(8, 'anglo_saxon_accounting')  # Insert after website
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg or 'Invalid field' in error_msg:
                print("    ⚠️  Note: 'Anglo-Saxon Accounting' field not available (module 'account_anglo_saxon' may not be installed)")
            # Continue without this field
        
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
    print("  [2/23] Exporting chart of accounts...")
    try:
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
    except Exception as e:
        print(f"    ❌ Error exporting accounts: {str(e)[:100]}")
        config['chart_of_accounts'] = []
    
    # 3. Export Account Groups
    print("  [3/23] Exporting account groups...")
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
    print("  [4/23] Exporting journals...")
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
    print("  [5/23] Exporting taxes...")
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
        # Get repartition lines details
        for tax in taxes:
            # Get invoice repartition lines
            if tax.get('invoice_repartition_line_ids'):
                try:
                    invoice_lines = models.execute_kw(
                        db, uid, password,
                        'account.tax.repartition.line', 'read',
                        [tax['invoice_repartition_line_ids']],
                        {'fields': ['repartition_type', 'account_id', 'factor_percent']}
                    )
                    tax['invoice_repartition_lines'] = invoice_lines
                except Exception as e:
                    print(f"      ⚠️  Warning: Could not export repartition lines for tax {tax.get('name')}: {str(e)[:80]}")
            
            # Get refund repartition lines
            if tax.get('refund_repartition_line_ids'):
                try:
                    refund_lines = models.execute_kw(
                        db, uid, password,
                        'account.tax.repartition.line', 'read',
                        [tax['refund_repartition_line_ids']],
                        {'fields': ['repartition_type', 'account_id', 'factor_percent']}
                    )
                    tax['refund_repartition_lines'] = refund_lines
                except Exception as e:
                    print(f"      ⚠️  Warning: Could not export refund lines for tax {tax.get('name')}: {str(e)[:80]}")
        config['taxes'] = taxes
        print(f"    ✓ Exported {len(taxes)} taxes")
    except Exception as e:
        print(f"    ❌ Error exporting taxes: {str(e)[:100]}")
        config['taxes'] = []
    
    # 6. Export Tax Groups
    print("  → Exporting tax groups...")
    # Get tax groups from taxes (tax_group_id)
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
    
    # 11. Export Bank Accounts (res.partner.bank)
    print("  → Exporting bank accounts...")
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
    
    # 12. Export Master Data từ ngs_sale module (CHỈ những bảng có company_id)
    print("  → Exporting ngs_sale master data (company-specific only)...")
    print("    ⚠️  Note: res.partner.type, supplier.delivery.type, sale.processing.state")
    print("       are shared across companies (no company_id) - SKIP export")
    
    # sale.commission.rate
    try:
        sale_commission_rates = models.execute_kw(
            db, uid, password,
            'sale.commission.rate', 'search_read',
            [[]],
            {'fields': ['name', 'from_qty', 'to_qty', 'supplier_id', 'rate', 'type']}
        )
        config['sale_commission_rates'] = sale_commission_rates
        print(f"    ✓ Exported {len(sale_commission_rates)} sale commission rates")
    except Exception as e:
        print(f"    ⚠️  Sale commission rates not available (permission/model): {str(e)[:100]}")
        config['sale_commission_rates'] = []
    
    # sale.commission.config
    try:
        sale_commission_configs = models.execute_kw(
            db, uid, password,
            'sale.commission.config', 'search_read',
            [[]],
            {'fields': ['name', 'commission_tool_id']}
        )
        config['sale_commission_configs'] = sale_commission_configs
        print(f"    ✓ Exported {len(sale_commission_configs)} sale commission configs")
    except Exception as e:
        print(f"    ⚠️  Sale commission configs not available (permission/model): {str(e)[:100]}")
        config['sale_commission_configs'] = []
    
    # sale.barem (SKIP - không có company_id, dùng chung)
    print("  → Skipping sale barems (shared across companies, no company_id)...")
    config['sale_barems'] = []
    
    # 13. Export Payment Terms (CHỈ những payment terms có company_id = company_id hiện tại)
    print("  → Exporting payment terms (company-specific only)...")
    payment_terms_company = models.execute_kw(
        db, uid, password,
        'account.payment.term', 'search_read',
        [[('company_id', '=', company_id)]],  # CHỈ export payment terms của company này
        {'fields': ['name', 'active', 'note', 'company_id']}
    )
    # Export lại với payment terms của company
    for pt in payment_terms_company:
        pt_id = pt['id']
        lines = models.execute_kw(
            db, uid, password,
            'account.payment.term.line', 'search_read',
            [[('payment_id', '=', pt_id)]],
            {'fields': ['value', 'value_amount', 'nb_days', 'option', 'days_after']}
        )
        pt['line_ids'] = lines
    config['payment_terms'] = payment_terms_company
    print(f"    ✓ Exported {len(payment_terms_company)} payment terms (company-specific)")
    print("    ⚠️  Note: Payment terms without company_id are shared - SKIP export")
    
    # 14. Export Account Groups (kiểm tra lại với filter đúng)
    print("  → Re-checking account groups...")
    account_groups_all = models.execute_kw(
        db, uid, password,
        'account.group', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': ['code_prefix_start', 'code_prefix_end', 'name', 'parent_id', 'company_id']}
    )
    # Update account groups nếu có
    if len(account_groups_all) > 0:
        config['account_groups'] = account_groups_all
        print(f"    ✓ Updated: Exported {len(account_groups_all)} account groups")
    else:
        print(f"    ⚠️  No account groups found for company {company_id}")
    
    # 15. Export Product Categories (SKIP - không có company_id, dùng chung)
    print("  → Skipping product categories (shared across companies, no company_id)...")
    config['product_categories'] = []
    
    # 16. Export Pricelists (nếu cần)
    print("  → Exporting pricelists...")
    try:
        pricelists = models.execute_kw(
            db, uid, password,
            'product.pricelist', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'active', 'currency_id', 'discount_policy']}
        )
        # Export pricelist items
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
    except Exception as e:
        print(f"    ⚠️  Pricelists not available: {str(e)[:100]}")
        config['pricelists'] = []
    
    # 17. Export Warehouses (nếu cần)
    print("  → Exporting warehouses...")
    warehouses = models.execute_kw(
        db, uid, password,
        'stock.warehouse', 'search_read',
        [[('company_id', '=', company_id)]],
        {'fields': ['name', 'code', 'active', 'partner_id', 'view_location_id', 'lot_stock_id']}
    )
    config['warehouses'] = warehouses
    print(f"    ✓ Exported {len(warehouses)} warehouses")
    
    # 18. Export Sequences (ir.sequence) cho journals và account moves
    print("  → Exporting sequences...")
    try:
        sequences = models.execute_kw(
            db, uid, password,
            'ir.sequence', 'search_read',
            [[('company_id', '=', company_id), '|', ('code', 'like', 'account.%'), ('code', 'like', 'journal.%')]],
            {'fields': ['name', 'code', 'prefix', 'suffix', 'padding', 'number_next', 'number_increment', 'use_date_range']}
        )
        config['sequences'] = sequences
        print(f"    ✓ Exported {len(sequences)} sequences")
    except Exception as e:
        print(f"    ⚠️  Sequences not available: {str(e)[:100]}")
        config['sequences'] = []
    
    # 19. Export Account Payment Methods (SKIP - không có company_id, dùng chung)
    print("  → Skipping payment methods (shared across companies, no company_id)...")
    config['payment_methods'] = []
    
    # 20. Export Account Reconcile Models
    print("  → Exporting account reconcile models...")
    try:
        reconcile_models = models.execute_kw(
            db, uid, password,
            'account.reconcile.model', 'search_read',
            [[('company_id', '=', company_id)]],
            {'fields': ['name', 'rule_type', 'match_text_location_label', 'match_text_location_note', 'match_text_location_reference', 'match_amount', 'match_amount_min', 'match_amount_max', 'match_label', 'match_note', 'match_transaction_type', 'match_same_currency', 'match_total', 'match_partner', 'line_ids']}
        )
        # Export reconcile model lines
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
    except Exception as e:
        print(f"    ⚠️  Reconcile models not available: {str(e)[:100]}")
        config['reconcile_models'] = []
    
    # 21. Export UOM Categories (SKIP - dùng chung, không có company_id)
    print("  → Skipping UOM categories (shared across companies, no company_id)...")
    config['uom_categories'] = []
    
    # 22. Export UOM Units (SKIP - dùng chung, không có company_id)
    print("  → Skipping UOM units (shared across companies, no company_id)...")
    config['uom_units'] = []
    
    # 23. Export Sale Order Fee (ngs_sale) - SKIP vì không có company_id, dùng chung
    print("  → Skipping sale order fees (shared across companies, no company_id)...")
    config['sale_order_fees'] = []
    
    # 24. Export Purchase Report Tool (ngs_sale) - SKIP vì không có company_id, dùng chung
    print("  → Skipping purchase report tools (shared across companies, no company_id)...")
    config['purchase_report_tools'] = []
    
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
    
    print(f"\n{'='*70}")
    print(f"✅ EXPORT COMPLETED SUCCESSFULLY")
    print(f"{'='*70}")
    print(f"📁 Output file: {output_file}")
    print(f"📊 File size: {output_file.stat().st_size / 1024:.2f} KB")
    print(f"\n{'='*70}")
    print(f"📊 EXPORT SUMMARY")
    print(f"{'='*70}")
    
    # Core Accounting Data
    print(f"\n📋 Core Accounting Data:")
    print(f"   ✓ Company: {config['company'].get('name', 'N/A')}")
    print(f"   ✓ Accounts: {len(config['chart_of_accounts'])}")
    print(f"   ✓ Account Groups: {len(config['account_groups'])}")
    print(f"   ✓ Journals: {len(config['journals'])}")
    print(f"   ✓ Taxes: {len(config['taxes'])}")
    print(f"   ✓ Tax Groups: {len(config['tax_groups'])}")
    print(f"   ✓ Fiscal Positions: {len(config['fiscal_positions'])}")
    print(f"   ✓ Payment Terms: {len(config['payment_terms'])}")
    print(f"   ✓ Bank Accounts: {len(config['bank_accounts'])}")
    
    # Master Data
    print(f"\n📦 Master Data:")
    print(f"   ✓ Pricelists: {len(config['pricelists'])}")
    print(f"   ✓ Warehouses: {len(config['warehouses'])}")
    print(f"   ✓ Sequences: {len(config['sequences'])}")
    print(f"   ✓ Reconcile Models: {len(config['reconcile_models'])}")
    print(f"   ✓ Sale Commission Rates: {len(config['sale_commission_rates'])}")
    print(f"   ✓ Sale Commission Configs: {len(config['sale_commission_configs'])}")
    
    # System
    print(f"\n⚙️  System Configuration:")
    print(f"   ✓ Config Parameters: {len(config['config_parameters'])}")
    print(f"   ✓ Account Tags: {len(config['account_tags'])}")
    
    # Skipped (Shared Data)
    print(f"\n⚠️  SKIPPED (Shared Across Companies - No company_id):")
    print(f"   - res.partner.type")
    print(f"   - supplier.delivery.type")
    print(f"   - sale.processing.state")
    print(f"   - sale.barem")
    print(f"   - sale.order.fee")
    print(f"   - purchase.report.tool")
    print(f"   - product.category")
    print(f"   - uom.category, uom.uom")
    print(f"   - account.payment.method")
    print(f"   - Payment Terms without company_id")
    
    # Total count
    total_records = (
        len(config['chart_of_accounts']) +
        len(config['account_groups']) +
        len(config['journals']) +
        len(config['taxes']) +
        len(config['fiscal_positions']) +
        len(config['payment_terms']) +
        len(config['bank_accounts']) +
        len(config['pricelists']) +
        len(config['sequences']) +
        len(config['reconcile_models'])
    )
    
    print(f"\n{'='*70}")
    print(f"📈 Total Records Exported: {total_records}")
    print(f"{'='*70}")
    print(f"\n💡 Next Steps:")
    print(f"   1. Review the exported file: {output_file.name}")
    print(f"   2. Test import on a test company first")
    print(f"   3. Backup database before importing to production")
    print(f"   4. Use import_accounting_config.py to import")
    print(f"\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
