import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusPricegroup(models.Model):
    _name = 'vendus.pricegroup'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Pricegroup'
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    title = fields.Char()
    is_default = fields.Boolean()
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    def prepare_create_vendus_record(self):
        return {
            'title'     : self.title,
            'is_default': self.is_default and 'on' or 'off'
        }

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id' : str(response['id']),
            'title'     : response['title'],
            'is_default': response['is_default'] == 'on',
            'company_id': self.env.company.id
        }

    @api.model
    def _get_endpoint_url(self):
        return 'products/pricegroups/'
