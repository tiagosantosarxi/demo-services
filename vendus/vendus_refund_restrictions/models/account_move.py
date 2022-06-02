from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        for rec in self:
            if rec.move_type == 'out_refund' and rec.company_id.country_id.code == 'PT':
                for line in rec.invoice_line_ids:
                    line.validate_refunded_qty()
        return super(AccountMove, self)._post(soft)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super(AccountMove, self)._reverse_moves(default_values_list, cancel)
        if cancel:
            return reverse_moves
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move, reverse_move in zip(self, reverse_moves):
            # UPDATE QUANTITY AND PRICE UNIT FOR CREDIT NOTES
            lines_to_unlink = self.env['account.move.line']
            for line, rev_line in zip(move.line_ids, reverse_move.line_ids):
                if rev_line.exclude_from_invoice_tab or rev_line.display_type:
                    continue
                refunded_qty = sum(
                    line.refund_line_ids.filtered(lambda l: l != rev_line and l.parent_state != 'cancel').mapped(
                        'quantity'))
                new_qty = line.quantity - refunded_qty
                if float_is_zero(new_qty, precision_digits=precision):
                    # If theres no available refund qty, remove line
                    lines_to_unlink |= rev_line
                    continue
                rev_line.with_context(check_move_validity=False).write({'quantity': new_qty})
                rev_line.with_context(check_move_validity=False)._onchange_price_subtotal()
            lines_to_unlink.with_context(check_move_validity=False).unlink()
            reverse_move.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)
            if not reverse_move.invoice_line_ids.filtered(lambda l: not l.display_type):
                raise UserError(_('There are not any available lines to refund.'))
        reverse_moves._check_balanced()
        return reverse_moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    refunded_line_id = fields.Many2one('account.move.line', string='Refunded Line', readonly=True, copy=False)
    refund_line_ids = fields.One2many('account.move.line', 'refunded_line_id', string='Refund Lines', readonly=True,
                                      copy=False)

    # pylint: disable=missing-return
    def _copy_data_extend_business_fields(self, values):
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        if 'move_reverse_cancel' in self.env.context and not self.env.context.get('rappel'):
            values['refunded_line_id'] = not self.exclude_from_invoice_tab and self.id

    def validate_refunded_qty(self):
        """
        Checks if refunded quantities are not superior to un-refunded quantities
        :return:
        """
        self.ensure_one()
        if not self.refunded_line_id:
            raise UserError(_('You can not create credit notes without origin invoices.'))
        refund_qty = sum(self.refunded_line_id.refund_line_ids.filtered(lambda l: l.parent_state != 'cancel').mapped(
            'quantity'))
        original_qty = self.refunded_line_id.quantity
        if refund_qty > original_qty:
            raise UserError(_('The refunded quantity should not be bigger than the original invoice line quantity: %s.',
                              original_qty))
