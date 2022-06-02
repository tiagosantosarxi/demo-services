import logging

from odoo import models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    vendus_id = fields.Char(readonly=True)
    vendus_order_id = fields.Char(readonly=True)

    def prepare_import_from_vendus(self, response, date, vendus_order_id):
        pos_payment_method = self.env['pos.payment.method'].search(
            [('vendus_payment_method_id.vendus_id', '=', response['id'])], limit=1)
        if not pos_payment_method:
            raise ValidationError(_("No payment method of Vendus found."))
        return {
            'vendus_id': str(response['id']),
            'name': response['title'],
            'company_id': self.env.company.id,
            'vendus_order_id': vendus_order_id,
            # 'pos_order_id': order.id,
            'amount': response['amount'],
            'payment_method_id': pos_payment_method.id,
            'payment_date': date,
        }
