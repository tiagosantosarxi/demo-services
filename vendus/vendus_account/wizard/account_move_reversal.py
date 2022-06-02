from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    is_reason_required = fields.Boolean(required=False, compute='_compute_is_reason_required')

    @api.depends('move_ids')
    def _compute_is_reason_required(self):
        for record in self:
            move_ids = record.move_ids._origin
            record.is_reason_required = any(move.vendus_id for move in move_ids)

    def reverse_moves(self):
        self.ensure_one()
        if self.move_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.journal_id.vendus_register_id.vendus_id):
            if len(self.journal_id | self.move_ids.mapped('journal_id')) > 1:
                raise ValidationError(_('You can not create credit notes for moves in different journals.'))
            if len(self.move_ids.mapped('company_id')) > 1:
                raise ValidationError(_('You can only create rappel credit notes from invoices of the same company.'))
            if len(self.move_ids.mapped('partner_id')) > 1:
                raise ValidationError(_('You can only create rappel credit notes from invoices with the same partner.'))
        return super(AccountMoveReversal, self).reverse_moves()

    def _prepare_default_reversal(self, move):
        """
        Remove "Refersal of" from the credit note ref since the vendus already does that.
        """
        vals = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        vals.update({
            'reason': self.reason
        })
        return vals
