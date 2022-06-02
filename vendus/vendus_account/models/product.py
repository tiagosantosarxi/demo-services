import base64
import logging

import requests

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'vendus.mixin']

    vendus_id = fields.Char(company_dependent=True)
    state = fields.Selection([('open', 'Open'), ('locked', 'Locked')], default='open', copy=False)

    @api.constrains('default_code')
    def _check_default_code_generation_type(self):
        """
        Checks if the product has a default code
        """
        for product in self:
            if product.state == 'locked':
                raise ValidationError(_('You cannot modify the internal reference of a product in posted documents.'))

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    def action_update_from_vendus(self):
        """
        Updates a product with the values from the vendus environment. Overrides info in Odoo.
        :return: True if operation was successful
        """
        self.ensure_one()
        if self.vendus_id:
            response = self.vendus_read()
            return self.write({
                'default_code'  : response['reference'],
                'barcode'       : response['barcode'],
                'name'          : response['title'],
                'standard_price': response['supply_price'],
                'list_price'    : response['gross_price'],
                'uom_id'        : response['unit_id'],
                'type'          : response['type_id'],
                'taxes_id'      : response['tax_id'],
                'categ_id'      : response['category_id'],
                'image_1920'    : response['image'],
            })

    @api.model
    def import_all_records_from_vendus(self, override=False):
        return super().import_all_records_from_vendus(override=True)

    def action_export_to_vendus(self):
        for rec in self:
            if rec.vendus_id:
                rec.vendus_update_exported()
            else:
                rec.vendus_export()

    def vendus_update_exported(self):
        self.ensure_one()
        response = self.vendus_request('patch', self._get_endpoint_url() + self.vendus_id, json=self.prepare_export_vendus_record())
        _logger.info(f'Vendus: {self._description} updated')
        return response

    def vendus_export(self):
        self.ensure_one()
        response = self.vendus_request('post', self._get_endpoint_url(), json=self.prepare_export_vendus_record())
        _logger.info(f'Vendus: {self._description} created with the id {response["id"]}')
        self.vendus_id = str(response['id'])
        return response

    # -------------------------------------------------------------------------
    # PREPARE METHODS
    # -------------------------------------------------------------------------

    def prepare_export_vendus_record(self, fast_create=False):
        """
        Prepares a dict with values to be passed to the product create method.
        :return: dict with values
        """
        tax = self.taxes_id.filtered(lambda t: t.company_id == self.env.company)
        vals = {
            'reference'        : self.default_code,
            'supplier_code'    : None,
            'title'            : self.name,
            'prices'           : {
                'supply': self.standard_price,
                'gross': self.list_price,
            },
            'unit_id'          : self.uom_id.get_vendus_uom(),
            'type_id'          : self.vendus_product_type(),
            'stock'            : {
                'control': int(self.type == 'product'),
                'type': self.vendus_stock_type(),
            },
            'category_id'      : self.categ_id.get_vendus_category(),
            'brand_id'         : None,
        }
        if tax.exemption_id:
            vals.update({
                'tax': {
                    'id': tax and tax[0].get_vendus_tax_type() or None,
                    'exemption': tax and tax.exemption_id.code or None,
                    'exemption_law': tax and tax.exemption_id.name or None,
                },
            })
        elif tax:
            vals.update({
                'tax': {
                    'id': tax and tax[0].get_vendus_tax_type() or None,
                },
            })
        if not fast_create:
            vals.update({
                'image'              : self.image_1920 and self.image_1920.decode('utf-8'),
                'include_description': 'no',
                'barcode'            : self.barcode
            })
        return vals

    def prepare_create_vendus_record(self, fast_create=False):
        """
        Prepares a dict with values to be passed to the product create method.
        :return: dict with values
        """
        tax = self.taxes_id.filtered(lambda t: t.company_id == self.env.company)
        vals = {
            'reference'        : self.default_code,
            'supplier_code'    : None,
            'title'            : self.name,
            'supply_price'     : self.standard_price,
            'gross_price'      : self.list_price,
            'unit_id'          : self.uom_id.get_vendus_uom(),
            'type_id'          : self.vendus_product_type(),
            'stock_control'    : int(self.type == 'product'),
            'stock_type'       : self.vendus_stock_type(),
            'tax_id'           : tax and tax[0].get_vendus_tax_type() or None,
            'tax_exemption'    : tax and tax.exemption_id.code or None,
            'tax_exemption_law': tax and tax.exemption_id.name or None,
            'category_id'      : self.categ_id.get_vendus_category(),
            'brand_id'         : None,
            'prices'           : None,
        }
        if not fast_create:
            # Vendus does not allow some fields to be passed when creating products with documents
            vals.update({
                'image'              : self.image_1920 and self.image_1920.decode('utf-8'),
                'include_description': 'no',
                'barcode'            : self.barcode
            })
        return vals

    def prepare_update_vendus_record(self):
        """
        Prepares a dict with values to be passed to the product update method.
        :return: dict with values
        """
        return self.prepare_create_vendus_record()

    @api.model
    def prepare_import_from_vendus(self, product):
        """
        Prepares the list of values to create the product in odoo from vendus
        :param product: dict with product values from the vendus API
        :return: dict with values to create the product in odoo
        """
        # tax = self.env['account.tax']
        # if product.get('tax') and product.get('tax').get('id') != '':
        #     tax = self.env['account.tax'].find_tax_by_vendus_id(product.get('tax').get('id'), product.get('tax').get('exemption'))
        categ = self.env['product.category']
        if product.get('category_id'):
            categ = self.env['product.category'].search_category_from_vendus_id(product.get('category_id'))
            if not categ:
                categ = categ.import_single_record_from_vendus(product.get('category_id'))
        vals = {
            'default_code'  : product.get('reference'),
            'barcode'       : product.get('barcode'),
            'name'          : product.get('title'),
            'standard_price': product.get('supply_price', 0),
            'list_price'    : product.get('price_without_tax'),
            'type'          : self.vendus_product_type2odoo(product),
            # 'taxes_id'      : tax and [(4, tax.id)],
            'categ_id'      : categ and categ.id,
            'active'        : product.get('status') == 'on',
            'vendus_id'     : product.get('id')
        }
        if not self.image_1920 and product.get('images'):
            try:
                vals.update({
                    'image_1920': base64.b64encode(requests.get(product.get('images').get('m')).content)
                })
            except requests.exceptions.HTTPError as httpe:
                _logger.warning('HTTP error %s with the given URL: %s' % (httpe.code, product.get('images').get('m')))
        return {k: v for k, v in vals.items() if v}

    def prepare_update_from_vendus(self, product):
        """
        Prepares the list of values to update the product in odoo from vendus
        :param product: dict with product values from the vendus API
        :return: dict with values to update product in odoo
        """
        vals = self.prepare_import_from_vendus(product)
        del vals['type']  # We should not update the type of an already created product
        if not self.vendus_id:
            vals.update({'vendus_id': product['id']})
        return vals

    @api.model
    def prepare_find_record_by_domain_list(self, record):
        """
        Override of abs method to include specific product matching domain
        :param record: product.product record
        :return: domain list
        """
        return [
            ('vendus_id', '=', record['id']),
            ('default_code', '=', record['reference']),
            ('barcode', '=', record['barcode']),
            ('name', '=ilike', record['title']),
        ]

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def vendus_product_type(self):
        """
        Converts the odoo product type into a vendus product type
        :return: valid vendus product type
        """
        return self.type in ('product', 'consu') and 'P' or self.type == 'service' and 'S' or 'O'

    def vendus_stock_type(self):
        """
        Converts the odoo stock type into a vendus stock type
        :return: valid vendus stock type
        """
        return self.type == 'consu' and 'P' or self.type == 'service' and 'S' or 'M'

    @api.model
    def vendus_product_type2odoo(self, product):
        """
        Converts the vendus product type into the odoo product type
        :param product: dict with the vendus product
        :return: valid odoo product type
        """
        return product['type_id'] == 'S' and 'service' or 'consu'

    def get_vendus_id_or_create_vals(self):
        """
        Returns a dict with the vendus_id for the product or the dict with the create values.
        :return: dict with id or values to create product
        """
        if self.vendus_id:
            return {'id': self.vendus_id}
        # return {'id': self.vendus_create()}
        vals = self.prepare_create_vendus_record(fast_create=True)
        return {k: v for k, v in vals.items() if v}

    @api.model
    def _get_endpoint_url(self):
        return 'products/'

    def lock(self):
        """
        Locks the product
        """

        self.filtered(lambda p: p.state == 'open').write({'state': 'locked'})


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vendus_id = fields.Char('Vendus ID', compute='_compute_vendus_id', inverse='_inverse_vendus_id')
    state = fields.Selection([('open', 'Open'), ('locked', 'Locked')], store=True, compute='_compute_state', copy=False)

    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.vendus_id')
    def _compute_vendus_id(self):
        unique_variants = self.filtered(lambda t: len(t.product_variant_ids) == 1)
        for template in unique_variants:
            template.vendus_id = template.product_variant_ids.vendus_id
        for template in (self - unique_variants):
            template.vendus_id = False

    @api.depends('product_variant_ids', 'product_variant_ids.state')
    def _compute_state(self):
        """
        Computing state by checking the state of active or archived product variants from this template
        :return:
        """
        for rec in self:
            prod_variant_ids = self.env['product.product'].search([
                ('product_tmpl_id', '=', rec.id), '|', ('active', '=', True), ('active', '=', False)])
            if any(state == 'locked' for state in prod_variant_ids.mapped('state')):
                rec.state = 'locked'
            else:
                rec.state = 'open'

    def _inverse_vendus_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.vendus_id = template.vendus_id

    def action_export_to_vendus(self):
        for rec in self:
            if len(rec.product_variant_ids) == 1:
                if rec.vendus_id:
                    rec.product_variant_ids.vendus_update_exported()
                else:
                    response = rec.product_variant_ids.vendus_export()
                    rec.vendus_id = str(response['id'])

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    def vendus_create(self):
        self.ensure_one()
        if len(self.product_variant_ids) == 1:
            return self.product_variant_ids.vendus_create()

    def vendus_update(self):
        self.ensure_one()
        if len(self.product_variant_ids) == 1:
            return self.product_variant_ids.vendus_update()

    @api.model
    def vendus_list(self):
        return self.env['product.product'].vendus_list()

    def vendus_read(self):
        self.ensure_one()
        if len(self.product_variant_ids) == 1:
            return self.product_variant_ids.vendus_read()

    def vendus_delete(self):
        self.ensure_one()
        if len(self.product_variant_ids) == 1:
            return self.product_variant_ids.vendus_delete()
