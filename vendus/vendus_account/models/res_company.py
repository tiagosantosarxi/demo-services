from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    vendus_api_key = fields.Char()
    vendus_test = fields.Boolean()
    vendus_active = fields.Boolean()
