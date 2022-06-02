import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockTransportLine(models.Model):
    _name = 'stock.transport.line'
    _description = "Stock Transport Lines"

    name = fields.Text(required=True)
    transport_id = fields.Many2one('stock.transport', ondelete='cascade')

    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    movement_type = fields.Selection(related='transport_id.movement_type')
    state = fields.Selection(related='transport_id.state')
    has_tracking = fields.Selection(related='product_id.tracking', string='Product with Tracking')
    lot_ids = fields.Many2many('stock.production.lot', string='Serial Numbers', readonly=False)

    @api.onchange('product_id', 'movement_type')
    def onchange_product_id(self):
        if self.product_id and self.transport_id:
            self.name = self.product_id._get_transport_description(self.movement_type)
        else:
            self.name = False

    @api.onchange('product_id')
    def _set_default_values(self):
        if self.product_id:
            if self.product_id.uom_id:
                self.product_uom = self.product_id.uom_id

    def prepare_return_line(self):
        return {
            'product_id'     : self.product_id.id,
            'name'           : self.name,
            'product_uom_qty': self.product_uom_qty,
            'product_uom'    : self.product_uom.id
        }
