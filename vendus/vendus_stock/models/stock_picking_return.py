from odoo import api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, picking_type_id = super()._create_returns()
        self.env['stock.picking'].browse(new_picking_id).write({'is_return': True})
        return new_picking_id, picking_type_id
