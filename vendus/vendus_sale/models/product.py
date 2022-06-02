import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def prepare_create_vendus_record(self, fast_create=False):
        vals = super(ProductProduct, self).prepare_create_vendus_record(fast_create)
        vals.update({
            'description': self.description_sale
        })
        return vals

    def get_vendus_id_or_create_vals(self):
        vals = super(ProductProduct, self).get_vendus_id_or_create_vals()
        vals.pop('description', None)
        return vals
