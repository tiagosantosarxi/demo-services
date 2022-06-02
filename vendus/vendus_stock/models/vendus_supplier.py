from odoo import api, fields, models, _


class VendusSupplier(models.Model):
    _name = 'vendus.supplier'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Supplier'

    vat = fields.Char()
    name = fields.Char()
    address = fields.Char()
    city = fields.Char()
    zip = fields.Char()
    phone = fields.Char()
    mobile = fields.Char()
    email = fields.Char()
    website = fields.Char()
    country_id = fields.Many2one('res.country')

    vendus_id = fields.Char(company_dependent=True)

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
                'address'   : response['address'],
                'city'      : response['city'],
                'zip'       : response['postalcode'],
                'phone'     : response['phone'],
                'mobile'    : response['mobile'],
                'email'     : response['email'],
                'website'   : response['website'],
                'country_id': country and country.id
            })

    def action_list_all_records(self):
        return self.vendus_list()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def prepare_create_vendus_record(self):
        """
        Prepares a dict with values to be passed to the supplier create method.
        :return: dict with values
        """
        vat = self.vat
        if vat and self.country_id.code != 'PT' and vat[:2] != self.country_id.code:
            vat = self.country_id.code + self.vat
        return {
            'name'              : self.name,
            'fiscal_id'         : vat,
            'address'           : self.address,
            'city'              : self.city,
            'postalcode'        : self.zip,
            'phone'             : self.phone,
            'mobile'            : self.mobile,
            'email'             : self.email,
            'website'           : self.website,
            'country'           : self.country_id.code,
        }

    def prepare_update_vendus_record(self):
        """
        Prepares a dict with values to be passed to the supplier update method.
        :return: dict with values
        """
        vals = self.prepare_create_vendus_record()
        return vals

    @api.model
    def prepare_import_from_vendus(self, supplier):
        """
        Prepares the list of values to create the supplier in odoo from vendus
        :param supplier: dict with supplier values from the vendus API
        :return: dict with values to create the supplier in odoo
        """
        country = self.env['res.country'].search([('code', '=', supplier['country'])])
        return {
            'name'      : supplier.get('name'),
            'vat'       : supplier.get('fiscal_id'),
            'address'   : supplier.get('address'),
            'city'      : supplier.get('city'),
            'zip'       : supplier.get('postalcode'),
            'phone'     : supplier.get('phone'),
            'mobile'    : supplier.get('mobile'),
            'email'     : supplier.get('email'),
            'website'   : supplier.get('website'),
            'country_id': country and country.id,
            'vendus_id' : supplier['id']
        }

    def prepare_update_from_vendus(self, customer):
        """
        Prepares the list of values to update the supplier in odoo from vendus
        :param customer: dict with supplier values from the vendus API
        :return: dict with values to update supplier in odoo
        """
        vals = self.prepare_import_from_vendus(customer)
        if not self.vendus_id:
            vals.update({'vendus_id': customer['id']})
        return vals

    @api.model
    def prepare_find_record_by_domain_list(self, record):
        """
        Override of abs method to include specific supplier matching domain
        :param record: vendus.supplier record
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
        Returns a dict with the vendus_id for the supplier or the dict with the create values.
        :return: dict with id or values to create supplier
        """
        if self.vendus_id:
            return {'id': self.vendus_id}
        vals = self.prepare_create_vendus_record()
        return {k: v for k, v in vals.items() if v}

    @api.model
    def _get_endpoint_url(self):
        return 'suppliers/'
