from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    at_foreign_partners = fields.Boolean(
        string="Use Foreign Partners",
        help="Check to use foreign partners with no official AT validation for Transport Documents"
    )
