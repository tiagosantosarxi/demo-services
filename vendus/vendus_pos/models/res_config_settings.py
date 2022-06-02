from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendus_url = fields.Char(related='company_id.vendus_url', readonly=False)
