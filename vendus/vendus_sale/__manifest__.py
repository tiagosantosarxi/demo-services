{
    'name': "Vendus Webservice - Portugal - Sale",

    'summary': """Vendus Webservice - Document Certification Portugal - Sale""",
    'author': "Arxi",
    'website': "https://www.arxi.pt",
    'category': 'Accounting',
    'version': '15.0.0.0.1',
    'license': 'OPL-1',
    'currency': 'EUR',
    'depends': ['vendus_account', 'sale_management', 'sale_journals'],
    'data': [
        'views/sale_journal_views.xml',
        'views/sale_order_views.xml',
        'wizard/sale_order_cancel_views.xml'
    ],
    'images': [],
    'auto_install': ['vendus_account', 'sale_management']
}
