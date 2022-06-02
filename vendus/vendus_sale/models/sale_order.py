from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'vendus.document.mixin']

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    def write(self, values):
        """
        Adds normal status when status changes
        """

        def vendus_needs_vendus_create_action(sale):
            return sale.state == 'draft' and sale.journal_id.vendus_register_id and sale.company_id.vendus_active

        if self.filtered(
                lambda sale: sale.state == 'draft' and sale.company_id.vendus_active and not sale.journal_id.vendus_register_id):
            raise ValidationError(_("The journal used must have Vendus Active."))
        needs_vendus_create_action = values.get('state') and self.filtered(vendus_needs_vendus_create_action) or \
                                     self.env['sale.order']
        res = super(SaleOrder, self).write(values)
        for rec in needs_vendus_create_action:
            rec.action_vendus_create()
        return res

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_vendus_create(self):
        """
        Creates the sale order in the Vendus webservice and returs the pdf and the vendus id
        :return:
        """
        self.ensure_one()
        if not all(len(line.tax_id) == 1 for line in self.order_line.filtered(lambda l: not l.display_type)):
            raise UserError(_('There must be one tax on each sale order line.'))
        self.remove_default_code_from_lines()
        response = self.vendus_create()
        self.name = response['number']
        if self.state == 'draft':
            self.state = 'sent'
        self.create_vendus_pdf(response['output'], response['number'])
        self.save_vendus_id_in_newly_created_products_and_customer()
        return True

    def action_cancel(self):
        """
        Restricts cancelling portuguese draft sale orders
        :return:
        """
        self.ensure_one()
        if self.state == 'draft' and self.company_id.country_id.code == 'PT':
            raise UserError(_(
                'You can not cancel a draft sale order. You should either edit or delete this record.'))
        cancel_warning = self._show_cancel_wizard()
        if not cancel_warning:
            self.vendus_update()
        return super(SaleOrder, self).action_cancel()

    def action_post(self):
        self.action_quotation_sent()

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    def vendus_update(self):
        response = super().vendus_update()
        return True

    @api.model
    def prepare_read_params(self):
        return {'mode': self.company_id.vendus_test and 'tests' or 'normal', 'output': 'pdf'}

    def prepare_update_vendus_record(self):
        return {'mode': self.company_id.vendus_test and 'tests' or 'normal', 'status': 'A'}

    @api.model
    def _get_endpoint_url(self):
        return 'documents/'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _show_cancel_wizard(self):
        """
        Shows cancel wizard (to add a reason for cancelling and to choose a cancel method) when it's a portuguese sale
        order.
        :return:
        """
        if self._context.get('disable_cancel_warning'):
            return False
        if any(rec.company_id.country_id.code == 'PT' for rec in self):
            return True
        return super(SaleOrder, self)._show_cancel_wizard()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(SaleOrder, self)._create_invoices(grouped, final, date)
        for move in moves:
            move._onchange_vendus_journal_id()
        return moves

    def prepare_create_vendus_record(self):
        vals = {
            'register_id'       : self.journal_id.vendus_register_id.vendus_id,
            'type'              : 'OT' if self.sale_type_id.code == 'OR' else self.sale_type_id.code,
            'date'              : self.date_order and self.date_order.date().isoformat() or False,
            'date_due'          : self.validity_date and self.validity_date.isoformat() or False,
            'mode'              : self.env.company.vendus_test and 'tests' or 'normal',
            'notes'             : self.note,
            'external_reference': self.client_order_ref,
            'client'            : self.partner_id.commercial_partner_id.get_vendus_id_or_create_vals(),
            'output'            : 'pdf',  # 'escpos' or 'html' is available
            'items'             : []
        }
        for line in self.order_line.filtered(lambda l: not l.display_type):
            item_dict = line.product_id.get_vendus_id_or_create_vals()
            item_dict.update({
                'qty'                : line.product_uom_qty,
                'title'              : line.name,
                'gross_price'        : line.price_unit if line.tax_id[0].price_include else line.price_unit * (
                        1 + line.tax_id[0].amount / 100),
                'discount_percentage': line.discount
            })
            if line.tax_id[0].country_region in ['PT', False]:
                tax_id = line.tax_id[0].get_vendus_tax_type()
                item_dict.update({
                    'tax_id': tax_id
                })
                if tax_id == 'ISE':
                    item_dict.update({
                        'tax_exemption': line.tax_id[0].exemption_id.code
                    })
            else:
                item_dict.update({
                    'tax_custom': {
                        'country': line.tax_id[0].country_region,
                        'rate'   : line.tax_id[0].amount,
                        'code'   : line.tax_id[0].amount and 'NOR' or 'ISE',
                        'type'   : 'IVA'
                    }
                })
                if 'tax_id' in item_dict:
                    item_dict.pop('tax_id')
            # Adicional text
            line_index = self.order_line.ids.index(line.id)
            if line_index < len(self.order_line) - 1:
                next_line = self.order_line[line_index + 1]
                if next_line.display_type == 'line_note':
                    item_dict.update({'text': next_line.name})
            vals['items'].append(item_dict)
        return vals

    def remove_default_code_from_lines(self):
        """
        Removes the default code before sending sale to vendus,
        since vendus does not expect default code to be in the text field
        :return: True if operation was successful
        """
        self.ensure_one()
        for line in self.order_line.filtered(lambda l: not l.display_type):
            line.name = line.name.replace(r'[%s]' % line.product_id.default_code, '').strip()
        return True

    def save_vendus_id_in_newly_created_products_and_customer(self):
        """
        If the invoice was done with product or customer creation, we need to save the vendus_id of those new records.
        :return: True if operation was sucessfull
        """
        response = self.vendus_read()
        if not self.partner_id.commercial_partner_id.vendus_id:
            self.partner_id.commercial_partner_id.vendus_id = response['client']['id']
        for line, item in zip(self.order_line.filtered(lambda l: not l.display_type), response['items']):
            if not line.product_id.vendus_id:
                line.product_id.vendus_id = item['id']
        return True
