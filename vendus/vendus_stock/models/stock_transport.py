import logging
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
UNKNOWN = 'Desconhecido'

UPDATABLE_FIELDS = (
    'start_date', 'end_date', 'vehicle_id', 'delivery_address_street', 'delivery_address_city',
    'delivery_address_zip', 'loading_address_street', 'loading_address_city', 'loading_address_zip',
    'transport_line_ids')


class StockTransport(models.Model):
    _name = 'stock.transport'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'vendus.document.mixin']
    _description = 'Stock Transport Document'
    _order = 'name desc, id desc'
    _check_company_auto = True

    def _get_default_partner_domain(self):
        company = self.company_id or self.env.company
        domain = []
        if not company.at_foreign_partners:
            domain = [('country_id', '=', company.country_id.id)]
        return domain

    @api.model
    def _get_default_journal(self):
        company = self.company_id or self.env.company
        if self._context.get('default_journal_id'):
            journal = self.env['stock.transport.journal'].browse(self._context['default_journal_id'])
        else:
            journal = self.env['stock.transport.journal'].search([('company_id', '=', company.id)], limit=1)
        return journal

    name = fields.Char(
        "Transport Document", required=True, copy=False, index=True, readonly=True, default=lambda self: _('New')
    )
    date = fields.Date(readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('cancel', 'Cancelled'),
        ('comm', 'Communication'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft'
    )
    transport_line_ids = fields.One2many('stock.transport.line', 'transport_id', string="Products", copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'stock.transport.journal',
        required=True,
        readonly=True,
        default=_get_default_journal,
        states={'draft': [('readonly', False)]},
        check_company=True
    )
    movement_type = fields.Selection(related='journal_id.movement_type', store=True)
    partner_id = fields.Many2one(
        'res.partner',
        readonly=True,
        required=False,
        states={'draft': [('readonly', False)]},
        domain=lambda self: self._get_default_partner_domain(),
    )
    origin_document = fields.Many2one('stock.transport', copy=False, readonly=True)
    return_documents = fields.One2many(
        'stock.transport',
        'origin_document',
        string="Related Return Documents",
        domain=[('movement_type', '=', 'returns.document')],
        copy=False,
        readonly=True
    )
    delivery_address_country = fields.Many2one(
        'res.country',
        readonly=True,
        default=lambda self: self.env.company.country_id
    )
    delivery_address_street = fields.Char(
        string="Delivery Address",
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]}
    )
    delivery_address_city = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]}
    )
    delivery_address_zip = fields.Char(
        string="Delivery Address Postal Code",
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]}
    )
    loading_address_country = fields.Many2one(
        'res.country',
        required=True,
        readonly=True,
        default=lambda self: self.env.company.country_id
    )
    loading_address_street = fields.Char(
        string="Loading Address",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]}
    )
    loading_address_city = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]}
    )
    loading_address_zip = fields.Char(
        string="Loading Address Postal Code",
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)], 'comm': [('readonly', False)]},
    )
    vehicle_id = fields.Char(string='Vehicle License Plate')
    note = fields.Text('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)]})
    start_date = fields.Datetime(
        required=False,
        states={'comm': [('required', True)], 'validated': [('required', True)], 'cancelled': [('required', True)]}
    )
    end_date = fields.Datetime()
    at_doc_code_id = fields.Char(string="AT Document Code ID", copy=False)
    foreign_partner = fields.Boolean(compute='_compute_foreign_partner')
    is_global = fields.Boolean()
    reference = fields.Char()

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('is_global')
    def onchange_is_global(self):
        if self.is_global:
            self.write({'partner_id': False})

    @api.onchange('partner_id')
    def _compute_foreign_partner(self):
        for rec in self:
            rec.foreign_partner = rec.partner_id.country_id != rec.company_id.country_id

    @api.onchange('partner_id')
    def set_delivery_address(self):
        if not self.partner_id:
            return self.update({
                'delivery_address_street' : False,
                'delivery_address_city'   : False,
                'delivery_address_zip'    : False,
                'delivery_address_country': False
            })

        addr = self.partner_id.address_get(['delivery'])
        addr_id = self.partner_id.browse(addr.get('delivery'))
        self.delivery_address_street = addr_id.street
        if addr_id.street2:
            self.delivery_address_street += (', ' + addr_id.street2)
        self.delivery_address_city = addr_id.city
        self.delivery_address_zip = addr_id.zip
        self.delivery_address_country = addr_id.country_id

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.vehicle_id = self.vehicle_id.upper()

    @api.onchange('date')
    def _onchange_date(self):
        """
        Raises warning when the posting date is bigger than today
        """

        if self.date and self.date > fields.Date.today():
            warning = {
                'title'  : _('Warning!'),
                'message': _('When posting in a future date, '
                             'you will only be able to create documents in a date after that.'),
            }
            return {'warning': warning}

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------

    def unlink(self):
        if self.filtered(lambda rec: rec.state != 'draft'):
            raise ValidationError(_('You can not unlink a posted document.'))
        return super().unlink()

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_generate_returns_document(self):
        returned = self.create(self.prepare_return_vals())
        action = self.env['ir.actions.act_window']._for_xml_id('vendus_stock.stock_transport_action')
        action.update({
            'res_id': returned.id,
            'views' : [(False, 'form')],
        })
        return action

    def action_validate(self):
        if self.state != 'draft':
            return ValidationError(_('You can not post a transport document that is already in a posted state.'))

        if not self.transport_line_ids:
            raise ValidationError(_('You can not post a transport document without any lines'))

        # Check date fields
        if not self.start_date:
            raise ValidationError(_('Movement Start Date is a required field'))

        # Adds today as the posting date if missing
        if not self.date:
            self.date = fields.Date.context_today(self)

        # Validate lots
        for line in self.transport_line_ids:
            if line.has_tracking == 'serial' and line.product_uom_qty != len(line.lot_ids):
                raise ValidationError(_('Line %s must have same the quantity serial numbers as product quantity.',
                                        line.name))
            elif line.has_tracking == 'lot' and len(line.lot_ids) != 1:
                raise ValidationError(_('You should have one line per product lot'))

        # Create document number
        response = self.vendus_create()
        self.name = response['number']
        self.create_vendus_pdf(response['output'], response['number'])
        self.save_vendus_id_in_newly_created_products_and_customer()
        return self.write({'state': 'validated'})

    def action_cancel(self):
        """
        Overrides the cancel method to update status
        """
        self.ensure_one()
        response = self.vendus_update()
        self.write({'state': 'cancel'})
        return True

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

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

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        res.update(self._default_loading_location())
        return res

    def _get_report_values(self, docids):
        docs = self.env['stock.transport'].browse(docids)
        return {
            'doc_ids'  : docs.ids,
            'doc_model': 'stock.transport',
            'docs'     : docs,
        }

    def prepare_return_vals(self):
        return_journal = self.journal_id.search(
            [('movement_type', '=', 'GD'), ('company_id', '=', self.company_id.id)], limit=1)
        if not return_journal:
            raise ValidationError(
                _('You must create a return type journal in this company to enable the return document creation'))
        return {
            'origin_document'         : self.id,
            'journal_id'              : return_journal.id,
            'partner_id'              : self.partner_id.id,
            'vehicle_id'              : self.vehicle_id or '',
            'delivery_address_street' : self.loading_address_street,
            'delivery_address_city'   : self.loading_address_city,
            'delivery_address_zip'    : self.loading_address_zip,
            'delivery_address_country': self.loading_address_country.id,
            'loading_address_street'  : self.delivery_address_street,
            'loading_address_city'    : self.delivery_address_city,
            'loading_address_zip'     : self.delivery_address_zip,
            'loading_address_country' : self.delivery_address_country.id,
            'transport_line_ids'      : [(0, 0, line.prepare_return_line()) for line in self.transport_line_ids]
        }

    def _default_loading_location(self):
        loading_location = self.env.company
        loading_address_street = loading_location.street
        if loading_location.street2:
            loading_address_street += (', ' + loading_location.street2)
        loading_address_city = loading_location.city
        loading_address_country = loading_location.country_id.id
        loading_address_zip = loading_location.zip

        return dict(
            loading_address_street=loading_address_street,
            loading_address_city=loading_address_city,
            loading_address_country=loading_address_country,
            loading_address_zip=loading_address_zip
        )

    def view_related_return_documents(self):
        return {
            'type'     : 'ir.actions.act_window',
            'name'     : _('Return Documents'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.transport',
            'domain'   : [('id', 'in', self.return_documents.ids)]
        }

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def prepare_create_vendus_record(self):
        start_date = self.start_date.replace(tzinfo=pytz.UTC).astimezone(tz=pytz.timezone('Portugal'))
        vals = {
            'register_id'       : self.journal_id.vendus_register_id.vendus_id,
            'type'              : self.journal_id.movement_type,
            'date'              : self.date.isoformat(),
            'date_supply'       : False,  # Tax point date (shipping info)
            'mode'              : self.env.company.vendus_test and 'tests' or 'normal',
            'external_reference': self.reference,
            'output'            : 'pdf',  # 'escpos' or 'html' is available
            'notes'             : self.note,
            'movement_of_goods' : {
                'vehicle_id' : self.vehicle_id,
                'show_prices': 'no',
                'loadpoint'  : {
                    'date'      : start_date.date().isoformat(),
                    'time'      : start_date.time().isoformat(timespec='minutes'),
                    'address'   : self.loading_address_street,
                    'postalcode': self.loading_address_zip,
                    'city'      : self.loading_address_city,
                    'country'   : self.loading_address_country and self.loading_address_country.code
                },
                'landpoint'  : {
                    'is_global' : self.is_global and 'yes' or 'no',
                    'date'      : self.end_date and self.end_date.date().isoformat(),
                    'time'      : self.end_date and self.end_date.time().isoformat(timespec='minutes')
                }
            },
            'items'             : []
        }
        if not self.is_global:
            vals['movement_of_goods']['landpoint'].update({
                'address'   : self.delivery_address_street,
                'postalcode': self.delivery_address_zip,
                'city'      : self.delivery_address_city,
                'country'   : self.delivery_address_country and self.delivery_address_country.code
            })
        if self.partner_id:
            if self.journal_id.movement_type == 'GD':
                supplier = self.partner_id.commercial_partner_id.vendus_supplier_id
                if not supplier:
                    supplier = self.env['vendus.supplier'].sudo().create(self.prepare_create_vendus_supplier())
                supplier_vals = supplier.get_vendus_id_or_create_vals()
                vals['supplier'] = supplier_vals
            else:
                if self.partner_id:
                    vals['client'] = self.partner_id.commercial_partner_id.get_vendus_id_or_create_vals()
        for line in self.transport_line_ids:
            item_dict = dict(
                line.product_id.get_vendus_id_or_create_vals(),
                qty=line.product_uom_qty,
                title=line.name
            )
            vals['items'].append(item_dict)
        return vals

    def prepare_create_vendus_supplier(self):
        return {
            'vat'       : self.partner_id.commercial_partner_id.vat,
            'name'      : self.partner_id.commercial_partner_id.name,
            'address'   : self.partner_id.commercial_partner_id.street,
            'city'      : self.partner_id.commercial_partner_id.city,
            'zip'       : self.partner_id.commercial_partner_id.zip,
            'phone'     : self.partner_id.commercial_partner_id.phone,
            'mobile'    : self.partner_id.commercial_partner_id.mobile,
            'email'     : self.partner_id.commercial_partner_id.email,
            'website'   : self.partner_id.commercial_partner_id.website,
            'country_id': self.partner_id.commercial_partner_id.country_id.id,
        }

    def remove_default_code_from_lines(self):
        """
        Removes the default code before sending invoice to vendus,
        since vendus does not expect default code to be in the text field
        :return: True if operation was successful
        """
        self.ensure_one()
        for line in self.transport_line_ids:
            line.name = line.name.replace(r'[%s]' % line.product_id.default_code, '').strip()
        return True

    def save_vendus_id_in_newly_created_products_and_customer(self):
        """
        If the document was done with product or customer creation, we need to save the vendus_id of those new records.
        :return: True if operation was sucessfull
        """
        response = self.vendus_read()
        if self.journal_id.movement_type == 'GD':
            if self.partner_id and not self.partner_id.commercial_partner_id.vendus_supplier_id.vendus_id:
                new_id = response.get('supplier', {'id': 0})['id']
                if not new_id:
                    new_id = response.get('client', {'id': 0})['id']
                self.partner_id.commercial_partner_id.vendus_supplier_id.vendus_id = new_id
        else:
            if self.partner_id and not self.partner_id.commercial_partner_id.vendus_id:
                self.partner_id.commercial_partner_id.vendus_id = response['client']['id']
        for line, item in zip(self.transport_line_ids, response['items']):
            if not line.product_id.vendus_id:
                line.product_id.vendus_id = item['id']
        return True
