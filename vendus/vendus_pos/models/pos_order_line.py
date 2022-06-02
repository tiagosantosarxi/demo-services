import logging
import math

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    vendus_order_id = fields.Char(related='order_id.vendus_id', string='Order Vendus ID')
    product_vendus_id = fields.Char(related='product_id.vendus_id', string='Product Vendus ID')

    @api.model
    def prepare_import_from_vendus(self, response, vendus_order_id):
        """
        Gets details of order and searchs for the necessary parameters to
        create a order line assigning values
        :return: data of order line
        """
        # order = self.env['pos.order'].search([('vendus_id', '=', vendus_order_id)], limit=1)
        product = self.env['product.product'].search([('vendus_id', '=', response['id'])])
        if not product:
            product = product.import_single_record_from_vendus(response['id'])

        domain = [
            ('amount', '=', self.env['account.tax'].vendus_id_2_amount(response['tax']['id'])),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ]
        if response['tax'].get('exemption'):
            domain.append(('exemption_id.code', '=', response['tax']['exemption']))
        tax = self.env['account.tax'].search(domain, limit=1)
        disc_amount = 0
        if 'discounts' in response:
            if 'amount' in response['discounts']:
                disc_amount = (response['discounts']['amount'] * 100) / response['amounts']['gross_total']
            elif 'percentage' in response['discounts']:
                disc_amount = response['discounts']['percentage']
        return {
            'name': response['title'],
            'full_product_name': response['title'],
            'product_id': product.id,
            'product_vendus_id': product.vendus_id,
            'company_id': self.env.company.id,
            # 'order_id': order.id,
            'tax_ids': tax,
            'discount': disc_amount,
            'vendus_order_id': vendus_order_id,
            'qty': response['qty'],
            'price_unit': response['amounts']['gross_unit'],
            'price_subtotal': self.round_decimals_down(float(response['amounts']['net_total']) - (
                    float(response['amounts']['net_total']) * (disc_amount / 100))),
            'price_subtotal_incl': self.round_decimals_down(float(response['amounts']['gross_total']) - (
                    float(response['amounts']['gross_total']) * (disc_amount / 100))),
        }

    @api.model
    def round_decimals_down(self, number, places=2):
        if places == 0:
            return math.floor(number)
        factor = 10 ** places
        return math.floor(number * factor) / factor
