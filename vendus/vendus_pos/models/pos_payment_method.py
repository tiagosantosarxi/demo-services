from odoo import api, fields, models


class VendusPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    _description = 'Payment Method'

    vendus_payment_method_id = fields.Many2one('vendus.payment.method', 'Vendus ID')
