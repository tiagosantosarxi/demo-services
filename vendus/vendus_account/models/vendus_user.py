import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusUser(models.Model):
    _name = 'vendus.user'
    _inherit = 'vendus.mixin'
    _description = 'Vendus User'
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    title = fields.Char()
    api_key = fields.Char()
    email = fields.Char()
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    @api.model
    def import_all_records_from_vendus(self, override=False):
        return super().import_all_records_from_vendus(override=True)

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id' : response['id'],
            'title'     : response['name'],
            'email'     : response['email'],
            'company_id': self.env.company.id
        }

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'account/users/'
