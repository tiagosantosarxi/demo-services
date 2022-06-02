from odoo import api, fields, models

UNKNOWN = 'Desconhecido'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_return = fields.Boolean(string='Is a Return Picking', readonly=True, copy=False)
    type = fields.Selection([
        ('out_picking', 'Delivery Slip'),
        ('in_picking', 'Vendor Delivery Slip'),
        ('out_refund', 'Return Delivery Slip'),
        ('in_refund', 'Vendor Return Delivery Slip'),
    ], readonly=True, states={'draft': [('readonly', False)]}, index=True, compute='_compute_type', store=True)
    stock_transport_ids = fields.Many2many('stock.transport')
    stock_transport_count = fields.Integer(compute='_compute_stock_transport_count')
    can_create_vendus_documents = fields.Boolean(compute='_compute_can_create_vendus_documents')

    # -------------------------------------------------------------------------
    # COMPUTE, CONSTRAINS AND ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.vendus_active', 'type')
    def _compute_can_create_vendus_documents(self):
        for rec in self:
            rec.can_create_vendus_documents = rec.company_id.vendus_active and rec.type in ('out_picking', 'out_refund')

    def _compute_stock_transport_count(self):
        for rec in self:
            rec.stock_transport_count = len(rec.stock_transport_ids)

    @api.depends('picking_type_id', 'is_return')
    def _compute_type(self):
        for rec in self:
            if not rec.is_return and rec.picking_type_id.code == 'outgoing':
                rec.type = 'out_picking'
            elif not rec.is_return and rec.picking_type_id.code == 'incoming':
                rec.type = 'in_picking'
            elif rec.is_return and rec.picking_type_id.code == 'incoming':
                rec.type = 'out_refund'
            elif not rec.is_return and rec.picking_type_id.code == 'outgoing':
                rec.type = 'in_refund'

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_create_at_transport(self):
        self.ensure_one()
        transport = self.env['stock.transport'].sudo().create(self._prepare_transport_values())
        self.stock_transport_ids = [(4, transport.id)]
        action = self.env['ir.actions.act_window']._for_xml_id('vendus_stock.stock_transport_action')
        action.update({
            'views' : [[False, 'form']],
            'res_id': transport and transport.id
        })
        return action

    def action_see_stock_transports(self):
        action = self.env['ir.actions.act_window']._for_xml_id('vendus_stock.stock_transport_action')
        action['domain'] = [('id', 'in', self.stock_transport_ids.ids)]
        return action

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def _prepare_transport_values(self):
        self.ensure_one()
        # Loading and Delivery Addresses
        dest_partner = self.partner_id
        load_partner = self.picking_type_id.warehouse_id.partner_id
        journal_domain = [('movement_type', '=', 'GT')]
        if self.is_return:
            dest_partner, load_partner = load_partner, dest_partner
            journal_domain = ([('movement_type', '=', 'GD')])
        journal = self.env['stock.transport.journal'].search(journal_domain, limit=1)

        vals = {
            'date'                    : fields.Date.today(),
            'company_id'              : self.company_id.id,
            'journal_id'              : journal.id,
            'partner_id'              : self.partner_id.id,
            'delivery_address_country': dest_partner.country_id.id,
            'delivery_address_street' : ' '.join((dest_partner.street or '', dest_partner.street2 or '')),
            'delivery_address_city'   : dest_partner.city,
            'delivery_address_zip'    : dest_partner.zip,
            'loading_address_country' : load_partner.country_id.id,
            'loading_address_street'  : ' '.join((load_partner.street or '', load_partner.street2 or '')),
            'loading_address_city'    : load_partner.city,
            'loading_address_zip'     : load_partner.zip,
            'note'                    : self.note
        }
        transport_lines = []
        for line in self.move_lines:
            if line.has_tracking == 'lot':
                transport_lines += [(0, 0, {
                    'name'           : stock_move_line.description_picking or stock_move_line.product_id.name,
                    'product_id'     : stock_move_line.product_id.id,
                    'product_uom_qty': stock_move_line.qty_done,
                    'product_uom'    : stock_move_line.product_uom_id.id,
                    'lot_ids'        : [(6, 0, stock_move_line.lot_id.ids)]
                }) for stock_move_line in line.move_line_ids]
            else:
                transport_lines += [(0, 0, {
                    'name'           : line.description_picking or line.product_id.name,
                    'product_id'     : line.product_id.id,
                    'product_uom_qty': line.quantity_done,
                    'product_uom'    : line.product_uom.id,
                    'lot_ids'        : [(6, 0, line.lot_ids.ids)]
                })]
        vals.update(transport_line_ids=transport_lines)
        return vals
