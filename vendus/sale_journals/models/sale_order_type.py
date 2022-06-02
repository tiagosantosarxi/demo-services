import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderType(models.Model):
    _name = 'sale.order.type'
    _description = 'Sale Document Type'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    code = fields.Char(size=10, required=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [('code_uniq', 'unique (code)', 'The code of the sale order type must be unique!')]

    def unlink(self):
        """
        Prevents deleting sale types with generated documents
        """
        if self.env['sale.order'].search_count([('sale_type_id', 'in', self.ids)]):
            raise ValidationError(_("You can not delete a sale document type that has generated documents"))
        return super(SaleOrderType, self).unlink()
