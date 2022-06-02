{
    'name': 'Vendus Webservice - Multiple Sale Journals',

    'summary': """Configure different sale journals and document types""",
    'author': "Arxi",
    'website': "https://www.arxi.pt",
    'category': 'Sales',
    'version': '15.0.0.0.1',
    'license': 'OPL-1',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/sale_order_type.xml',
        'report/sale_order_templates.xml',
        'views/sale_order_type_views.xml',
        'views/sale_order_journal_views.xml',
        'views/sale_order_views.xml',
        'views/sale_journals_menus.xml'
    ],
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook'
}
