from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendus_api_key = fields.Char(related='company_id.vendus_api_key', readonly=False)
    vendus_test = fields.Boolean(related='company_id.vendus_test', readonly=False)
    vendus_active = fields.Boolean(related='company_id.vendus_active', readonly=False)
