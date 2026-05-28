# -*- coding: utf-8 -*
# TL Technology (thanhchatvn@gmail.com)
{
    "name": "NSG Sale (Kinh Doanh Thép Nam Sài Gòn)",
    "version": "0.0.1",
    "category": "Sale",
    "author": "thanhchatvn@gmail.com",
    "summary":
        """
        NGS Sale Management, Kinh Doanh Thép Nam Sài Gòn
        """,
    "description":
        """
        NGS Sale Management, Kinh Doanh Thép Nam Sài Gòn \n
        """,
    "sequence": 0,
    "depends": [
        "sale_margin",
        "sale_stock_margin",
        "sale_expense_margin",
        "purchase",
        "delivery",
        "sale_purchase_inter_company_rules",
        "sale_purchase",
        "sale_stock",
        "account_reports",
        "account_followup",
    ],
    "demo": [],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "datas/configs/config_parameter.xml",
        "datas/configs/res_partner_type_datas.xml",
        "datas/configs/supplier_delivery_type.xml",
        "datas/configs/sale_processing_state.xml",
        "datas/configs/cron_invoice_order_id.xml",
        "views/account_followup_views.xml",
        "views/account_journal.xml",
        "views/product_pricelist_item_views.xml",
        "views/account_payment.xml",
        "views/account_payment_term.xml",
        "views/product_views.xml",
        "views/purchase_report_tool.xml",
        "views/purchase_order.xml",
        "views/res_company.xml",
        "views/report_layout_templates.xml",
        "views/res_partner.xml",
        "views/res_partner_type.xml",
        "views/account_move.xml",
        "views/supplier_delivery_type.xml",
        "views/res_config_settings.xml",
        "views/sale_barem.xml",
        "views/sale_order.xml",
        "views/sale_report_views.xml",
        "views/sale_processing_state.xml",
        "views/sale_commission_tool.xml",
        "views/stock_picking.xml",
        "views/sale_commission_user.xml",
        "wizards/import_sale_order.xml",
        "wizards/import_sale_order_config.xml",
        "wizards/account_partner_reconciliation_view.xml",
        "reports/partner_ledger.xml",
        "reports/report_sale_order.xml",
        "reports/report_purchasequotation_document.xml",
        "reports/report_purchase_order_line.xml",
        "reports/account_invoice_report_views.xml",
        "reports/invoice_payment_analysis_report_views.xml",
        "reports/delivery_receipt_report.xml",
    ],
    "qweb": [

    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "external_dependencies": {},
    "images": ["static/description/icon.png"],
    "support": "thanhchatvn@gmail.com",
    "license": "OPL-1",
    "post_init_hook": "_auto_clean_cache_when_installed",
    "assets": {
        "point_of_sale.assets": [

        ],
        "web.assets_common": [
            "ngs_sale/static/src/css/ngs_sale.css",
        ],
        "point_of_sale.pos_assets_backend": [

        ],
        "web.assets_qweb": [

        ],
    },
}
