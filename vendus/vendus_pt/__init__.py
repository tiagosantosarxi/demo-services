from odoo import SUPERUSER_ID, api


def _post_init_hook(cr, registry):
    """
    This generates exemption taxes for portuguese companies (if they already exist on the server)
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    taxes_with_exemption = env['account.tax.template'].search([
        ('chart_template_id', '=', env.ref('l10n_pt.pt_chart_template').id), ('exemption_id', '!=', False)
    ])
    for pt_company in env['res.company'].search([('partner_id.country_id.code', '=', 'PT')]):
        taxes_with_exemption._generate_tax(pt_company)
