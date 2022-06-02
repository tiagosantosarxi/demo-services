import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'vendus.mixin']

    display_name = fields.Char(compute='_compute_display_name')
    vendus_receipt_name = fields.Char()
    vendus_id = fields.Char(company_dependent=False)
    vendus_attachment_id = fields.Many2one('ir.attachment', string="Vendus PDF", required=False, copy=False)
    reason = fields.Char(help="Reason for the status update", size=50, copy=False, readonly=True)
    origin_move_ids = fields.Many2many('account.move', string='Invoices', copy=False)
    vendus_payment_method_id = fields.Many2one(
        'vendus.payment.method', readonly=True, states={'draft': [('readonly', False)]}, copy=False
    )
    needs_vendus_payment_method = fields.Boolean(compute='_compute_needs_vendus_payment_method')

    @api.depends('name', 'vendus_receipt_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.vendus_receipt_name or rec.name

    @api.onchange('line_ids')
    def _compute_needs_vendus_payment_method(self):
        self.needs_vendus_payment_method = any(self.line_ids.mapped('move_id.vendus_id'))

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_post(self):
        def vendus_needs_vendus_create_action(p):
            return p.company_id.vendus_active and p.payment_type == 'inbound' and p.partner_type == 'customer' \
                   and not p.vendus_id and not any(p.origin_move_ids.mapped('vendus_is_self_paid'))

        res = super().action_post()
        # Validate Fields
        if not self.env.context.get('vendus_self_paid'):
            for rec in self.filtered(vendus_needs_vendus_create_action):
                rec.check_invoice_residual()
                # Vendus Create
                response = rec.vendus_create()
                rec.vendus_receipt_name = response['number']
                # Save PDF
                self.env.cr.commit()  # pylint: disable=invalid-commit
                rec.create_vendus_pdf(response['output'], response['number'])

        return res

    def action_cancel(self):
        res = super(AccountPayment, self).action_cancel()
        if self.vendus_id:
            self.vendus_update()
        return res

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    def vendus_read(self):
        response = super().vendus_read()
        self.create_pdf(response['output'], response['number'])
        return response

    @api.model
    def _get_endpoint_url(self):
        """
        Returns the relative endpoint of the model. Eg: 'products/'
        :return: string with the model relative endpoint
        """
        return 'documents/'

    # -------------------------------------------------------------------------
    # PREPARE METHODS
    # -------------------------------------------------------------------------

    def prepare_create_vendus_record(self):
        """
        Prepares a dict to create a vendus record through the Vendus API.
        :return: dict with values
        """
        vals = {
            'register_id'       : self.origin_move_ids[0].journal_id.vendus_register_id.vendus_id,
            'type'              : 'RG',
            'date'              : self.date.isoformat(),
            'mode'              : self.env.company.vendus_test and 'tests' or 'normal',
            'notes'             : self.narration,
            'external_reference': self.ref,
            'client'            : self.partner_id.commercial_partner_id.get_vendus_id_or_create_vals(),
            'output'            : 'pdf',  # 'escpos' or 'html' is available
            'payments'          : [{
                'id'    : self.vendus_payment_method_id.vendus_id,
                'amount': self.amount_total_signed
            }],
            'invoices'          : [{
                'document_number': inv.name
            } for inv in self.origin_move_ids.filtered('vendus_id')]
        }

        return vals

    def prepare_update_vendus_record(self):
        """
        Prepares a dict to update a vendus record through the Vendus API.
        :return: dict with values
        """
        return {'mode': self.company_id.vendus_test and 'tests' or 'normal', 'status': 'A'}

    @api.model
    def prepare_read_params(self):
        return {'mode': self.company_id.vendus_test and 'tests' or 'normal', 'output': 'pdf'}

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def create_pdf(self, binary, name):
        """
        Downloads and creates an attachment for the vendus invoice document
        """

        if not self.vendus_attachment_id:
            doc_name = "".join([name.replace('/', '-'), ".pdf"])

            values = {
                'name'       : doc_name,
                'store_fname': doc_name,
                'res_model'  : 'account.payment',
                'res_id'     : self.id,
                'type'       : 'binary',
                'public'     : True,
                'datas'      : binary,
            }
            self.vendus_attachment_id = self.env['ir.attachment'].sudo().create(values)
        return self.vendus_attachment_id

    @api.model
    def _get_endpoint_url(self):
        return 'documents/'

    def check_invoice_residual(self):
        """
        Checks if the residual amount for the selected invoices is not less than the payment amount
        """
        self.ensure_one()
        if not self.origin_move_ids:
            self.origin_move_ids = self.payment_transaction_id.invoice_ids
            if not self.origin_move_ids:
                raise ValidationError(_("You can not post a payment without an origin invoice."))
            if self.origin_move_ids.filtered(lambda m: not m.vendus_id and m.journal_id.vendus_register_id):
                raise ValidationError(_('You can not post a payment for invoices without a vendus document.'))

    def create_vendus_pdf(self, binary, name):
        """
        Downloads and creates an attachment for the vendus document
        """

        if not self.vendus_attachment_id:
            doc_name = "".join([name.replace('/', '-'), ".pdf"])

            values = {
                'name'       : doc_name,
                'store_fname': doc_name,
                'res_model'  : 'account.payment',
                'res_id'     : self.id,
                'type'       : 'binary',
                'public'     : True,
                'datas'      : binary,
            }
            self.vendus_attachment_id = self.env['ir.attachment'].sudo().create(values)
        return self.vendus_attachment_id


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    vendus_payment_method_id = fields.Many2one('vendus.payment.method')
    needs_vendus_payment_method = fields.Boolean(compute='_compute_needs_vendus_payment_method')

    @api.onchange('line_ids')
    def _compute_needs_vendus_payment_method(self):
        self.needs_vendus_payment_method = any(self.line_ids.mapped('move_id.vendus_id'))

    def _create_payment_vals_from_wizard(self):
        """
        Adds the origin_move_ids from the payment wizard into the payment record.
        This allows us to link and validated invoices to be paid, directly from the payment.
        :return: dict with values to create the account payment
        """
        values = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        values.update({
            'origin_move_ids'         : [(6, 0, self.line_ids.mapped('move_id').ids)],
            'vendus_payment_method_id': self.vendus_payment_method_id.id
        })
        return values
