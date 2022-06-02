from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendus_supplier_id = fields.Many2one('vendus.supplier', company_dependent=True)
