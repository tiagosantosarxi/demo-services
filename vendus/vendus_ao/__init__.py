from odoo import SUPERUSER_ID, api


def _post_init_hook(cr, registry):
    """
    This generates exemption taxes for angolan companies (if they already exist on the server)
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    taxes_with_exemption = env['account.tax.template'].search([
        ('chart_template_id', '=', env.ref('l10n_ao.l10n_ao_chart_template').id), ('exemption_id', '!=', False)
    ])
    for ao_company in env['res.company'].search([('partner_id.country_id.code', '=', 'AO')]):
        taxes_with_exemption._generate_tax(ao_company)
