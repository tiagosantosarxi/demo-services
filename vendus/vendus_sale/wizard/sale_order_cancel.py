from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    display_invoice_alert = fields.Boolean(compute='_compute_display_invoice_alert')
    display_reason_field = fields.Boolean(compute='_compute_display_reason_field')
    reason = fields.Char(size=50)
    is_rewrite = fields.Boolean()
    cancel_method = fields.Selection(selection=[
        ('cancel', 'Cancel'),
        ('rewrite', 'Cancel and new draft quotation'),
        ('proforma', 'Cancel and new proforma invoice')
    ],
        string='Cancel Method',
        default='cancel',
        required=True,
        help='Choose how you want to cancel this sale order. You cannot "proforma" if the record is already a proforma.'
    )

    def action_cancel(self):
        if self.cancel_method == 'proforma' and self.order_id.sale_type_id == self.env.ref('sale_journals.t_proforma'):
            raise UserError(_('You can not convert a proforma into a proforma. Use the "cancel" or "rewrite" options.'))
        reason = self.cancel_method == 'proforma' and _('Converted into proforma') or self.reason
        self.order_id.write({'reason': reason})
        res = super(SaleOrderCancel, self).action_cancel()
        if self.cancel_method in ('rewrite', 'proforma'):
            new_sale = self.order_id.copy(self._prepare_copy_values())
            return {
                'type'     : 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'res_id'   : new_sale.id,
                'context'  : dict(self.env.context, form_view_initial_mode='edit'),
            }
        return res

    def _prepare_copy_values(self):
        values = dict()
        if self.cancel_method == 'proforma':
            proforma = self.env.ref('sale_journals.t_proforma')
            journal = self.env['sale.order.journal'].search([
                ('sale_type_id', '=', proforma.id), ('company_id', '=', self.order_id.company_id.id)], limit=1)
            values.update({'journal_id': journal and journal.id, 'sale_type_id': proforma.id})
        return values

    @api.onchange('order_id', 'cancel_method')
    def _compute_display_reason_field(self):
        self.display_reason_field = self.order_id.company_id.country_id.code == 'PT' and self.cancel_method != 'proforma'
