import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockTransportJournal(models.Model):
    _name = 'stock.transport.journal'
    _description = 'Stock Document Journal'
    _order = 'sequence, name desc, id desc'
    _check_company_auto = True

    _sql_constraints = [
        ('name_uniq', 'unique (name, company_id)', "This name is already being used in another journal!"),
    ]

    name = fields.Char(required=True, index=True)
    movement_type = fields.Selection(
        selection=[
            ('GR', 'Delivery Document'),
            ('GD', 'Returns Document'),
            ('GA', 'Own Assets Document'),
            ('GT', 'Transport Slip')],
        required=True,
        string="Operation Type"
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    sequence = fields.Integer('Display order', default=10, copy=False)
    vendus_register_id = fields.Many2one('vendus.register')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % (self.name or ''))
        return super(StockTransportJournal, self).copy(default)
