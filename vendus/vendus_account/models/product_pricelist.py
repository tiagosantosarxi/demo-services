import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    vendus_pricegroup_id = fields.Many2one('vendus.pricegroup', company_dependent=True)
