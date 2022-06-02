{
    'name': "Vendus Webservice - POS",

    'summary': """Vendus Webservice - POS Integration""",
    'author': "Arxi",
    'website': "https://www.arxi.pt",
    'category': 'Accounting',
    'version': '15.0.0.0.1',
    'license': 'OPL-1',
    'depends': ['payment', 'vendus_account', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/cron.xml',
        'data/final_consumer.xml',
        'views/pos_order_view.xml',
        'views/pos_payment_method_views.xml',
        'views/vendus_payment_method_views.xml',
        'views/res_company.xml',
        'views/res_config_settings.xml',
        'views/pos_config_views.xml',
    ],
    'images': [],
    'application': True,
    'auto_install': True,
}
