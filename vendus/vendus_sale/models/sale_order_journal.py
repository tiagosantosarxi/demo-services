from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'sale.order.journal'

    vendus_register_id = fields.Many2one('vendus.register')
