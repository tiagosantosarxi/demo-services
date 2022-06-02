{
    'name': "Vendus Webservice - Portugal - Stock",

    'summary': """Vendus Webservice - Document Certification Portugal - Stock""",
    'author': "Arxi",
    'website': "https://www.arxi.pt",
    'category': 'Inventory/Delivery',
    'version': '15.0.0.0.1',
    'license': 'OPL-1',
    'currency': 'EUR',
    'depends': ['stock', 'vendus_account'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/stock_picking_views.xml',
        'views/transport_document_views.xml',
        'views/transport_document_journal_views.xml',
        'report/transport_document_report.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'images': [],
    'auto_install': True,
    'post_init_hook': '_post_init_hook'
}
