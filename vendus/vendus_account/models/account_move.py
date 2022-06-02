import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'vendus.document.mixin']

    vat_note = fields.Html(related='fiscal_position_id.note', string='VAT Note')
    is_vendus_credit_note = fields.Boolean(compute='_compute_is_vendus_credit_note')
    show_reset_to_draft_button = fields.Boolean(compute='_compute_show_reset_to_draft_button')
    reason = fields.Char(states={'draft': [('readonly', False)]})
    vendus_payment_method_id = fields.Many2one('vendus.payment.method', string="Payment Method")
    vendus_is_self_paid = fields.Boolean()
    vendus_payment_journal_id = fields.Many2one('account.journal', string="Payment Journal")

    # @api.onchange('vendus_payment_method_id')
    # def _onchange_vendus_payment_method_id(self):
    #     self.vendus_payment_journal_id = self.vendus_payment_method_id and self.vendus_payment_method_id.default_payment_journal_id or \
    #                                      self.env['account.journal']

    @api.onchange('journal_id')
    def _onchange_vendus_journal_id(self):
        self.vendus_is_self_paid = self.journal_id and self.journal_id.vendus_register_id and self.journal_id.vendus_document_type in [
            'FR', 'FS']

    @api.depends('journal_id', 'move_type')
    def _compute_is_vendus_credit_note(self):
        for rec in self:
            rec.is_vendus_credit_note = rec.journal_id.vendus_register_id and rec.move_type == 'out_refund'

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def _post(self, soft=True):
        """
        When posting an invoice for a company with a vendus_key, we create the vendus record as well.
        If we're posting a vendus credit note, we should reconcile directly with the original invoice to avoid further
        problems.
        :param soft:
        :return:
        """
        res = super(AccountMove, self)._post(soft)
        if self.filtered(
                lambda m: m.move_type == 'out_invoice' and m.company_id.vendus_active and not m.journal_id.vendus_register_id):
            raise ValidationError(_("The journal used must have Vendus Active."))
        for move in self.filtered(
                lambda m: m.company_id.vendus_active and m.journal_id.vendus_register_id and not m.vendus_id):
            self.remove_default_code_from_lines()
            if not all(len(line.tax_ids) == 1 for line in move.invoice_line_ids.filtered(lambda l: not l.display_type)):
                raise ValidationError(_('There must be one tax on each invoice line.'))
            if move.move_type == 'out_invoice' and move.vendus_is_self_paid:
                # Removes non-needed fields
                move.invoice_payment_term_id = False
                payment_id = self.env['account.payment'].create(move.invoice_pay_now_payment_create())
                payment_id.with_context(vendus_self_paid=True).action_post()
                (payment_id.move_id + move).mapped('line_ids').filtered(
                    lambda x: x.account_internal_type in ('receivable', 'payable')).reconcile()
            if 'vendus_update' not in self.env.context:
                response = move.vendus_create()
                move.name = response['number']
                self.env.cr.commit()
                move.create_vendus_pdf(response['output'], response['number'])
                move.save_vendus_id_in_newly_created_products_and_customer()
            else:
                for order in move.pos_order_ids:
                    if order.state != 'invoiced':
                        move.pos_order_ids.browser(order).vendus_update()
                        move.name = order.name
                self.env.cr.commit()  # pylint: disable=invalid-commit
            if move.move_type == 'out_refund':
                # Reconcile with original invoice
                refunded_lines = move.line_ids.mapped('refunded_line_id.move_id.line_ids').filtered(
                    lambda line: line.account_id.reconcile or line.account_id.internal_type == 'liquidity')
                move.js_assign_outstanding_line(refunded_lines.ids)
            (move.partner_id | move.commercial_partner_id).sudo().lock()
            move.invoice_line_ids.mapped('product_id').sudo().lock()
        return res

    def invoice_pay_now_payment_create(self):
        """
        Prepare payment values for selfpaid invoices
        """
        payment_journal_id = self.get_payment_journal_id()
        if self.move_type == 'out_invoice':
            payment_methods = payment_journal_id.outbound_payment_method_line_ids[0]
            payment_type = 'inbound'
            partner_type = 'customer'
        elif self.move_type == 'in_invoice':
            payment_methods = payment_journal_id.inbound_payment_method_line_ids[0]
            payment_type = 'outbound'
            partner_type = 'supplier'
        else:
            return
        return {
            'journal_id'       : self.vendus_payment_journal_id.id,
            'payment_type'     : payment_type,
            'payment_method_line_id': payment_methods.id,
            'partner_type'     : partner_type,
            'partner_id'       : self.partner_id.commercial_partner_id.id,
            'amount'           : self.amount_total,
            'currency_id'      : self.currency_id.id,
            'date'             : self.date,
            'company_id'       : self.company_id.id,
            'ref'              : self.name,
            'origin_move_ids'  : [(6, 0, self.ids)]
        }

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """
        Override reverse move creation method to include the unrefunded quantities for credit note lines
        """
        reverse_moves = super(AccountMove, self)._reverse_moves(default_values_list, cancel)
        if cancel:
            return reverse_moves
        for move, reverse_move in zip(self, reverse_moves):
            # UPDATE QUANTITY FOR CREDIT NOTES
            lines_to_unlink = self.env['account.move.line']
            for line, rev_line in zip(move.line_ids, reverse_move.line_ids):
                if rev_line.exclude_from_invoice_tab or rev_line.display_type:
                    continue
                refund_line_ids = line.refund_line_ids.filtered(lambda l: l != rev_line and l.parent_state != 'cancel')
                refunded_qty = sum(refund_line_ids.mapped('quantity'))
                rev_line.with_context(check_move_validity=False).write({'quantity': line.quantity - refunded_qty})
                rev_line.with_context(check_move_validity=False)._onchange_price_subtotal()

            lines_to_unlink.with_context(check_move_validity=False).unlink()
            reverse_move.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)

            if not reverse_move.invoice_line_ids.filtered(lambda l: not l.display_type):
                raise ValidationError(_('There are not any available lines to refund.'))

        reverse_moves._check_balanced()
        return reverse_moves

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    @api.model
    def prepare_read_params(self):
        return {'mode': self.company_id.vendus_test and 'tests' or 'normal', 'output': 'pdf'}

    @api.model
    def _get_endpoint_url(self):
        return 'documents/'

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def get_payment_method_id(self):
        return self.vendus_payment_method_id and self.vendus_payment_method_id.vendus_id or \
               self.journal_id.default_vendus_payment_method_id and self.journal_id.default_vendus_payment_method_id.vendus_id

    def get_payment_journal_id(self):
        return self.vendus_payment_journal_id or self.journal_id.default_vendus_payment_journal_id

    def prepare_create_vendus_record(self):
        vals = {
            'register_id': self.journal_id.vendus_register_id.vendus_id,
            'type': self.move_type == 'out_invoice' and self.journal_id.vendus_document_type or 'NC',
            'date': self.invoice_date.isoformat(),
            'date_due': self.invoice_date_due.isoformat(),
            'date_supply': False,  # Tax point date (shipping info)
            'mode': self.env.company.vendus_test and 'tests' or 'normal',
            'notes': self.narration,
            'external_reference': self.ref,
            'client': self.commercial_partner_id.get_vendus_id_or_create_vals(),
            'output': 'pdf',  # 'escpos' or 'html' is available
            'items': []
        }
        if self.vendus_is_self_paid:
            vals.update({
                'payments': [
                    {
                        'id': self.get_payment_method_id(),
                        'amount': self.amount_total,
                        'date_due': self.invoice_date_due.isoformat()
                    }
                ]
            })
        if self.move_type == 'out_refund':
            vals.update({
                'notes': self.reason
            })
        elif self.fiscal_position_id.note:
            vals['notes'] = '\n'.join([self.fiscal_position_id.note, vals['notes'] if vals['notes'] else ''])

        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            item_dict = dict(line.product_id.get_vendus_id_or_create_vals(), qty=line.quantity)
            if self.move_type == 'out_invoice':
                item_dict.update({
                    'title'              : line.name,
                    'gross_price'        : line.price_unit if line.tax_ids[0].price_include else line.price_unit * (
                                1 + line.tax_ids[0].amount / 100),
                    'discount_percentage': line.discount
                })
                if line.tax_ids[0].country_region in ['PT', False]:
                    tax_id = line.tax_ids[0].get_vendus_tax_type()
                    item_dict.update({
                        'tax_id': tax_id
                    })
                    if tax_id == 'ISE':
                        item_dict.update({
                            'tax_exemption': line.tax_ids[0].exemption_id.code
                        })
                else:
                    item_dict.update({
                        'tax_custom': {
                            'country': line.tax_ids[0].country_region,
                            'rate': line.tax_ids[0].amount,
                            'code': line.tax_ids[0].amount and 'NOR' or 'ISE',
                            'type': 'IVA'
                        }
                    })
                    if 'tax_id' in item_dict:
                        item_dict.pop('tax_id')

                # Adicional text
                line_index = self.invoice_line_ids.ids.index(line.id)
                if line_index < len(self.invoice_line_ids) - 1:
                    next_line = self.invoice_line_ids[line_index + 1]
                    if next_line.display_type == 'line_note':
                        item_dict.update({'text': next_line.name})

            else:
                item_dict.update({
                    'reference_document': {
                        'document_number': self.reversed_entry_id.name,
                        'document_row'   : line.find_line_index_on_move()
                    }
                })
            vals['items'].append(item_dict)
        return vals

    def remove_default_code_from_lines(self):
        """
        Removes the default code before sending invoice to vendus,
        since vendus does not expect default code to be in the text field
        :return: True if operation was successful
        """
        self.ensure_one()
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            line.name = line.name.replace(r'[%s]' % line.product_id.default_code, '').strip()
        return True

    def save_vendus_id_in_newly_created_products_and_customer(self):
        """
        If the invoice was done with product or customer creation, we need to save the vendus_id of those new records.
        :return: True if operation was sucessfull
        """
        response = self.vendus_read()
        if not self.commercial_partner_id.vendus_id:
            self.commercial_partner_id.vendus_id = response['client']['id']
        for line, item in zip(self.invoice_line_ids.filtered(lambda l: not l.display_type), response['items']):
            if not line.product_id.vendus_id:
                line.product_id.vendus_id = item['id']
        return True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    refunded_line_id = fields.Many2one('account.move.line', string='Refunded Line', readonly=True, copy=False)
    refund_line_ids = fields.One2many('account.move.line', 'refunded_line_id', string='Refund Lines', readonly=True,
                                      copy=False)

    # pylint: disable=missing-return
    def _copy_data_extend_business_fields(self, values):
        """
        Add refuned_line_id as a field to be populated when generating a credit note
        """
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        if 'move_reverse_cancel' in self.env.context:
            values['refunded_line_id'] = not self.exclude_from_invoice_tab and self.id

    def find_line_index_on_move(self):
        """
        Finds the index of the refunded line in the refunded document. Vendus expects the sequence starting with 1.
        :return: invoice line index in the refunded move (starting at 1)
        """
        return self.move_id.reversed_entry_id.invoice_line_ids.filtered(lambda l: not l.display_type).ids.index(
            self.refunded_line_id.id) + 1
