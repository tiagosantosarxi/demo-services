from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    tax_obj = env['ir.model.data'].search([('module', '=', 'vendus_account'), ('model', 'in', ['account.tax.exemption', 'account.tax.template', 'account.tax'])])
    tax_obj.write({
        'module': 'vendus_pt'
    })
