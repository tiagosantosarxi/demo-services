from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    at_foreign_partners = fields.Boolean(
        string="Use Foreign Partners", related='company_id.at_foreign_partners', readonly=False
    )
