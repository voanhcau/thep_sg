#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export/Import Translations từ Company 1 → Company 2

Script này export translations (ir.translation) từ công ty nguồn và import vào công ty đích.

Cơ chế:
- Translations được lưu trong model `ir.translation`
- Mỗi translation có: name (model,field), res_id (record ID), lang, value
- Export translations cho các records của company 1 (accounts, taxes, etc.)
- Import vào company 2 với res_id mapping
- **LUÔN UPDATE** translations nếu đã tồn tại (overwrite)

Usage:
    # Export
    python export_import_translations.py export [env] [source_company_id] [output_file.json]
    
    # Import
    python export_import_translations.py import [env] [input_file.json] [target_company_id]
    
Example:
    python export_import_translations.py export local 1 translations_company_1.json
    python export_import_translations.py import test translations_company_1.json 2
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

def export_translations(models, uid, password, db, company_id):
    """
    Export translations từ company nguồn
    
    Export translations cho các models:
    - account.account (name)
    - account.tax (name, description)
    - account.fiscal.position (name)
    - account.journal (name)
    - account.payment.term (name)
    - product.template (name)
    - product.category (name)
    """
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
    
    # Models và fields cần export translations
    models_to_export = [
        {
            'model': 'account.account',
            'fields': ['name'],
            'key_field': 'code',  # Dùng code để map
        },
        {
            'model': 'account.tax',
            'fields': ['name', 'description'],
            'key_field': 'name',  # Dùng name để map
        },
        {
            'model': 'account.fiscal.position',
            'fields': ['name'],
            'key_field': 'name',
        },
        {
            'model': 'account.journal',
            'fields': ['name'],
            'key_field': 'code',  # Dùng code để map
        },
        {
            'model': 'account.payment.term',
            'fields': ['name'],
            'key_field': 'name',
        },
        {
            'model': 'product.template',
            'fields': ['name'],
            'key_field': 'default_code',  # Dùng default_code để map
        },
        {
            'model': 'product.category',
            'fields': ['name'],
            'key_field': 'name',
        },
    ]
    
    total_translations = 0
    
    for model_config in models_to_export:
        model_name = model_config['model']
        fields = model_config['fields']
        key_field = model_config['key_field']
        
        print(f"  → Exporting translations for {model_name}...")
        
            # Lấy tất cả records của company
        try:
            # Một số models có thể không có company_id, cần xử lý riêng
            search_domain = []
            if model_name in ['account.account', 'account.tax', 'account.fiscal.position', 
                             'account.journal', 'account.payment.term']:
                search_domain = [('company_id', '=', company_id)]
            elif model_name == 'product.template':
                # Product có thể dùng chung, nhưng có thể filter theo company nếu cần
                search_domain = []  # Lấy tất cả products (dùng chung)
            elif model_name == 'product.category':
                search_domain = []  # Product category dùng chung
            
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
            
            # Với mỗi record, lấy translations
            for record in records:
                record_id = record['id']
                key_value = record.get(key_field, '')
                
                # Lấy translations cho từng field
                for field in fields:
                    # Lấy giá trị gốc (default language)
                    original_value = record.get(field, '')
                    if not original_value:
                        continue
                    
                    # Lấy danh sách ngôn ngữ
                    try:
                        langs = models.execute_kw(
                            db, uid, password,
                            'res.lang', 'search_read',
                            [[]],
                            {'fields': ['code', 'name']}
                        )
                    except:
                        langs = []
                    
                    # Với mỗi ngôn ngữ, đọc record để lấy translated value
                    for lang in langs:
                        lang_code = lang.get('code', '')
                        if not lang_code or lang_code == 'en_US':  # Skip English (default)
                            continue
                        
                        try:
                            # Đọc record với context lang
                            record_with_lang = models.execute_kw(
                                db, uid, password,
                                model_name, 'read',
                                [[record_id]],
                                {'fields': [field], 'context': {'lang': lang_code}}
                            )
                            
                            if record_with_lang and record_with_lang[0].get(field):
                                translated_value = record_with_lang[0][field]
                                
                                # Chỉ export nếu có translation và khác với giá trị gốc
                                if translated_value and translated_value != original_value:
                                    translations_data['translations'].append({
                                        'model': model_name,
                                        'field': field,
                                        'res_id': record_id,
                                        'key_value': key_value,  # Dùng để map khi import
                                        'lang': lang_code,
                                        'value': translated_value,
                                        'src': original_value,
                                    })
                                    total_translations += 1
                        except Exception as e:
                            # Skip nếu không đọc được với ngôn ngữ này
                            continue
            
            print(f"    ✓ Exported {len([t for t in translations_data['translations'] if t['model'] == model_name])} translations")
            
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg or 'Invalid field' in error_msg:
                print(f"    ⚠️  Model {model_name} not available: {str(e)[:100]}")
            else:
                print(f"    ⚠️  Error exporting {model_name}: {str(e)[:100]}")
    
    print(f"\n{'='*70}")
    print(f"✅ EXPORT COMPLETED")
    print(f"{'='*70}")
    print(f"📊 Total translations exported: {total_translations}")
    print(f"{'='*70}\n")
    
    return translations_data

def import_translations(models, uid, password, db, import_data, target_company_id):
    """
    Import translations vào company đích
    
    Logic:
    1. Group translations theo model
    2. Với mỗi model, build mapping: key_value (code/name) → res_id trong target company
    3. Tạo translations mới với res_id đã map
    """
    print(f"\n{'='*70}")
    print(f"📥 IMPORTING TRANSLATIONS")
    print(f"{'='*70}")
    print(f"Target Company ID: {target_company_id}")
    print(f"Source Company ID: {import_data.get('source_company_id', 'N/A')}")
    print(f"⚠️  MODE: UPDATE translations if they exist (will overwrite existing translations)")
    print(f"{'='*70}\n")
    
    # Group translations theo model
    translations_by_model = defaultdict(list)
    for trans in import_data.get('translations', []):
        translations_by_model[trans['model']].append(trans)
    
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process từng model
    for model_name, translations in translations_by_model.items():
        print(f"  → Processing {model_name}...")
        
        # Xác định key_field để map
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
        
        # Build mapping: key_value → res_id trong target company
        print(f"    → Building {key_field} → res_id mapping...")
        
        # Lấy tất cả records của target company
        try:
            # Một số models có thể không có company_id
            search_domain = []
            if model_name in ['account.account', 'account.tax', 'account.fiscal.position', 
                             'account.journal', 'account.payment.term']:
                search_domain = [('company_id', '=', target_company_id)]
            elif model_name in ['product.template', 'product.category']:
                search_domain = []  # Products và categories dùng chung
            
            target_records = models.execute_kw(
                db, uid, password,
                model_name, 'search_read',
                [search_domain],
                {'fields': ['id', key_field]}
            )
            
            # Build mapping
            key_to_id = {}
            for record in target_records:
                key_value = record.get(key_field, '')
                if key_value:
                    key_to_id[key_value] = record['id']
            
            print(f"    ✓ Mapped {len(key_to_id)} records")
            
        except Exception as e:
            print(f"    ⚠️  Error getting target records: {str(e)[:100]}")
            continue
        
        # Import translations
        print(f"    → Importing {len(translations)} translations...")
        
        for trans in translations:
            key_value = trans.get('key_value', '')
            target_res_id = key_to_id.get(key_value)
            
            if not target_res_id:
                skipped_count += 1
                continue
            
            # Set translation bằng cách write vào record với context lang
            # Odoo sẽ tự động tạo/update ir.translation
            try:
                # Write vào record với context lang để set translation
                models.execute_kw(
                    db, uid, password,
                    model_name, 'write',
                    [[target_res_id], {
                        trans['field']: trans['value']
                    }],
                    {'context': {'lang': trans['lang']}}
                )
                success_count += 1
                if success_count <= 20:  # Log 20 đầu tiên
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
    print(f"\n💡 Note: Translations are UPDATED if they already exist (not skipped)")
    print(f"{'='*70}\n")
    
    return {
        'success': success_count,
        'skipped': skipped_count,
        'errors': error_count
    }

def main():
    if len(sys.argv) < 2:
        print("="*70)
        print("📋 USAGE")
        print("="*70)
        print("Export:")
        print("  python export_import_translations.py export [env] [company_id] [output_file.json]")
        print("\nImport:")
        print("  python export_import_translations.py import [env] [input_file.json] [target_company_id]")
        print("\nExample:")
        print("  python export_import_translations.py export local 1 translations_company_1.json")
        print("  python export_import_translations.py import test translations_company_1.json 2")
        print("="*70)
        return 1
    
    action = sys.argv[1].lower()
    
    if action == 'export':
        if len(sys.argv) < 5:
            print("❌ Missing arguments for export")
            print("Usage: export [env] [company_id] [output_file.json]")
            return 1
        
        env_type = sys.argv[2]
        company_id = int(sys.argv[3])
        output_file = Path(sys.argv[4])
        
        print(f"🔗 Connecting to {env_type} environment...")
        url, db, username, password, models, uid = get_connection(env_type)
        print(f"✅ Connected to {url} (DB: {db})")
        
        # Export
        translations_data = export_translations(models, uid, password, db, company_id)
        
        if translations_data:
            # Save to JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(translations_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"📁 Output file: {output_file}")
            print(f"📊 Translations exported: {len(translations_data['translations'])}")
            return 0
        else:
            print("❌ Export failed")
            return 1
    
    elif action == 'import':
        if len(sys.argv) < 5:
            print("❌ Missing arguments for import")
            print("Usage: import [env] [input_file.json] [target_company_id]")
            return 1
        
        env_type = sys.argv[2]
        input_file = Path(sys.argv[3])
        target_company_id = int(sys.argv[4])
        
        if not input_file.exists():
            print(f"❌ Input file not found: {input_file}")
            return 1
        
        print(f"🔗 Connecting to {env_type} environment...")
        url, db, username, password, models, uid = get_connection(env_type)
        print(f"✅ Connected to {url} (DB: {db})")
        
        # Load import data
        with open(input_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Import
        result = import_translations(models, uid, password, db, import_data, target_company_id)
        
        print(f"📊 Final Results:")
        print(f"   ✓ Success: {result['success']}")
        print(f"   ⏭️  Skipped: {result['skipped']}")
        print(f"   ⚠️  Errors: {result['errors']}")
        return 0
    
    else:
        print(f"❌ Unknown action: {action}")
        print("Use 'export' or 'import'")
        return 1

if __name__ == '__main__':
    sys.exit(main())
