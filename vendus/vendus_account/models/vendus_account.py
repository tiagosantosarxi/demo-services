import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusAccount(models.Model):
    _name = 'vendus.account'
    _inherit = 'vendus.mixin'
    _description = 'Vendus account'
    _rec_name = 'title'

    title = fields.Char()
    url = fields.Char()
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id' : str(response['id']),
            'title'     : response['company'],
            'company_id': self.env.company.id,
            'url'       : response['url'],
        }

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'account/'
