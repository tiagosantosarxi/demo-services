import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'vendus.mixin']

    vendus_id = fields.Char(company_dependent=True)
    state = fields.Selection([('open', 'Open'), ('locked', 'Locked')], string='Partner State', default='open',
                             copy=False)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_update_from_vendus(self):
        self.ensure_one()
        if self.vendus_id:
            response = self.vendus_request('get', self._get_endpoint_url() + str(self.vendus_id))
            country = self.env['res.country'].search([('code', '=', response['country'])])
            return self.write({
                'name'      : response['name'],
                'vat'       : response['fiscal_id'],
                'ref'       : response['external_reference'],
                'street'    : response['address'],
                'city'      : response['city'],
                'zip'       : response['postalcode'],
                'phone'     : response['phone'],
                'mobile'    : response['mobile'],
                'email'     : response['email'],
                'website'   : response['website'],
                'country_id': country and country.id,
                'active'    : response['status'],
                'comment'   : response['notes']
            })

    def action_list_all_records(self):
        return self.vendus_list()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def prepare_create_vendus_record(self):
        """
        Prepares a dict with values to be passed to the partner create method.
        :return: dict with values
        """
        vat = self.vat
        if vat and self.country_id and self.country_id.code != 'PT' and vat[:2] != self.country_id.code:
            vat = self.country_id.code + self.vat
        return {
            'name'              : self.name,
            'fiscal_id'         : vat,
            'external_reference': self.ref,
            'address'           : self.street,
            'city'              : self.city,
            'postalcode'        : self.zip,
            'phone'             : self.phone,
            'mobile'            : self.mobile,
            'email'             : self.email,
            'website'           : self.website,
            'country'           : self.country_id.code,
            'notes'             : self.comment
        }

    def prepare_update_vendus_record(self):
        """
        Prepares a dict with values to be passed to the partner update method.
        :return: dict with values
        """
        vals = self.prepare_create_vendus_record()
        vals.update({
            'status': self.active and 'active' or 'inactive'
        })
        return vals

    @api.model
    def prepare_import_from_vendus(self, customer):
        """
        Prepares the list of values to create the customer in odoo from vendus
        :param customer: dict with customer values from the vendus API
        :return: dict with values to create the customer in odoo
        """
        country = self.env['res.country'].search([('code', '=', customer['country'])])
        return {
            'name'      : customer.get('name'),
            'vat'       : customer.get('fiscal_id'),
            'ref'       : customer.get('external_reference'),
            'street'    : customer.get('address'),
            'city'      : customer.get('city'),
            'zip'       : customer.get('postalcode'),
            'phone'     : customer.get('phone'),
            'mobile'    : customer.get('mobile'),
            'email'     : customer.get('email'),
            'website'   : customer.get('website'),
            'country_id': country and country.id,
            'active'    : customer['status'],
            'comment'   : customer.get('notes'),
            'vendus_id' : customer.get('id')
        }

    def prepare_update_from_vendus(self, customer):
        """
        Prepares the list of values to update the customer in odoo from vendus
        :param customer: dict with customer values from the vendus API
        :return: dict with values to update partner in odoo
        """
        vals = self.prepare_import_from_vendus(customer)
        if not self.vendus_id:
            vals.update({'vendus_id': customer['id']})
        return vals

    @api.model
    def prepare_find_record_by_domain_list(self, record):
        """
        Override of abs method to include specific partner matching domain
        :param record: res.partner record
        :return: domain list
        """
        vat = record['fiscal_id']
        if len(record['fiscal_id']) > 1 and record['fiscal_id'][:2] == record['country']:
            vat = record['fiscal_id'][2:]
        return [
            ('vendus_id', '=', record['id']),
            ('vat', '=', vat),
            ('vat', '=', record['country'] + vat),
            ('name', '=ilike', record['name']),
            ('email', '=', record['email'])
        ]

    @api.model
    def import_all_records_from_vendus(self, override=False):
        return super().import_all_records_from_vendus(override=True)

    def get_vendus_id_or_create_vals(self):
        """
        Returns a dict with the vendus_id for the customer or the dict with the create values.
        Beware: Vendus Hack! Since vendus doesn't allow for document creation with client creation without a VAT number,
         we need to create the partner before sending the invoice to the vendus API.
        :return: dict with id or values to create customer
        """
        if self.vendus_id:
            return {'id': self.vendus_id}
        if not self.vat and not self.ref:
            response = self.vendus_create()
            # We need to force the commit of the transaction here to prevent losing information if there's an
            # exception in a following vendus API call.
            self.env.cr.commit()  # pylint: disable=invalid-commit
            return {'id': response['id']}
        vals = self.prepare_create_vendus_record()
        return {k: v for k, v in vals.items() if v}

    @api.model
    def search_user_from_vendus_id(self, vendus_id):
        user = self.search([('vendus_id', '=', vendus_id)], limit=1)
        if not user:
            vendus_user = self.env['vendus.user'].search([('vendus_id', '=', vendus_id),
                                                          ('company_id', '=', self.env.company.id)], limit=1)
            if not vendus_user:
                vendus_user = vendus_user.import_single_record_from_vendus(vendus_id)
            user = self.search([('name', '=', vendus_user.title), ('email', '=', vendus_user.email)], limit=1)
            if not user:
                user = self.create({
                    'name': vendus_user.title,
                    'email': vendus_user.email,
                    'vendus_id': vendus_user.vendus_id
                })
            else:
                user.write({
                    'vendus_id': vendus_user.vendus_id
                })
        return user

    @api.model
    def _get_endpoint_url(self):
        return 'clients/'

    def write(self, vals):
        """
        Adds a portuguese VAT number validation
        Checks if you're updating name or vat for partners with invoices
        """

        for partner in self:
            if partner.state == 'locked':
                if 'vat' in vals and partner.vat and partner.vat != '999999990' and vals['vat'] != partner.vat:
                    country_code = partner.country_id and partner.country_id.code.upper() or ''
                    if not (vals['vat'] and vals['vat'] in (country_code + partner.vat, partner.vat[2:])):
                        raise UserError(_('You cannot modify the VAT of a partner with posted documents.'))
                if 'name' in vals and 'vat' not in vals and not partner.vat:
                    raise UserError(
                        _('You cannot modify the name of a partner without a VAT number and with posted documents.'))

        return super(ResPartner, self).write(vals)

    def lock(self):
        """
        Locks partner
        """

        self.filtered(lambda p: p.state == 'open').write({'state': 'locked'})
