# -*- coding: utf-8 -*-
{
    "name": "ACB Bank Integration",
    "version": "16.0.1.0.0",
    "category": "Banking",
    "summary": "Tích hợp API ngân hàng ACB để nhận thông báo giao dịch",
    "description": """
        Module tích hợp API ngân hàng ACB
    """,
    "author": "NSG ERP Team",
    "website": "https://nsgerp.com",
    "depends": [
        "base",
        "account",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/acb_transaction_views.xml",
        "views/acb_config_views.xml",
        "views/acb_fetch_wizard_views.xml",
        "views/menu_views.xml",
        "data/acb_config_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "nsg_acb_integration/static/src/css/acb_styles.css",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
} 