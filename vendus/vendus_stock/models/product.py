import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def vendus_product_type2odoo(self, product):
        res = super(ProductProduct, self).vendus_product_type2odoo(product)
        if product.get('stock_control') == 1:
            return 'product'
        return res

    def _get_transport_description(self, code):
        """
        Returns the product receipt/delivery/picking description depending on the type of transport
        """

        self.ensure_one()
        description = self.name
        if code == 'GD' and self.description_pickingin:
            description += '\n' + self.description_pickingin
        if code in ('GR', 'GT') and self.description_pickingout:
            description += '\n' + self.description_pickingout
        if code == 'GA' and self.description_picking:
            description += '\n' + self.description_picking
        return description
