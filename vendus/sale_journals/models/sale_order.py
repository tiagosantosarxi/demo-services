from datetime import datetime

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('sale', 'Confirmed'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ])

    @api.model
    def _default_journal(self):
        """
        Computes the default journal based on context
        """

        company_id = self._context.get('company_id', self.env.company.id)
        domain = [('company_id', '=', company_id)]
        code = self._context.get('default_sale_type')
        if code:
            type_id = self.env['sale.order.type'].search([('code', '=', code)], limit=1)
            domain += [('sale_type_id', '=', type_id.id)]
        return self.env['sale.order.journal'].search(domain, limit=1)

    @api.model
    def _journal_domain(self):
        """
        Gets the journal domain for the selected document type
        """
        domain = [('company_id', '=?', self.company_id.id)]
        code = self._context.get('default_sale_type')
        if code:
            type_id = self.env['sale.order.type'].search([('code', '=', code)], limit=1)
            domain += [('sale_type_id', '=', type_id.id)]
        else:
            domain += [('sale_type_id.code', '!=', 'PF')]
        return domain

    journal_id = fields.Many2one(
        comodel_name='sale.order.journal',
        default=_default_journal,
        domain=lambda self: self._journal_domain(),
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        check_company=True
    )
    sale_type_id = fields.Many2one(related='journal_id.sale_type_id', string='Sale Type', copy=True)
    sale_type = fields.Char(related='journal_id.sale_type_id.name', string='Sale Type Name', copy=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True, string='Company Currency')
    # pylint: disable=method-compute
    amount_total_company = fields.Monetary(
        string='Total Amount in Company Currency',
        currency_field='company_currency_id',
        store=True,
        readonly=True,
        compute='_amount_all'
    )
    amount_untaxed_company = fields.Monetary(
        string='Untaxed Amount in Company Currency',
        currency_field='company_currency_id',
        store=True,
        readonly=True,
        compute='_amount_all'
    )

    # pylint: disable=missing-return
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self)._amount_all()
        for order in self:
            info = (order.company_currency_id, order.company_id, order.date_order or datetime.now())
            order.amount_total_company = order.currency_id._convert(order.amount_total, *info)
            order.amount_untaxed_company = order.currency_id._convert(order.amount_untaxed, *info)

    @api.model
    def create(self, vals):
        """
        Adds draft as a name to prevent adding a sequence before hashing
        """
        vals['name'] = _('Draft')
        return super(SaleOrder, self).create(vals)

    def write(self, values):
        """
        Adds a sequence when the status changes from draft
        """
        if 'state' in values and values.get('state') not in ('draft', 'cancel'):
            # we need to sort sales by date because sales selected in a tree view are unsorted
            sales_to_post = self.filtered(lambda sale: sale.state == 'draft').sorted('date_order')
            for rec in sales_to_post:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(rec.date_order))
                rec.name = rec.sudo().journal_id.sequence_id.next_by_id(sequence_date=seq_date)
        res = super(SaleOrder, self).write(values)
        return res
