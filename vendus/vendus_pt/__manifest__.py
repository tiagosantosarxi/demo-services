{
    'name': "Vendus Webservice - Portugal",

    'summary': """Vendus Webservice - Document Certification - Portugal""",
    'author': "Arxi",
    'website': "https://www.arxi.pt",
    'category': 'Accounting',
    'version': '15.0.0.0.1',
    'license': 'OPL-1',
    'depends': ['l10n_pt', 'vendus_account'],
    'data': [
        'data/account_tax_exemption.xml',
        'data/account_tax_template.xml',
    ],
    'images': [],
    'auto_install': True,
    'post_init_hook': '_post_init_hook'
}