import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusRegister(models.Model):
    _name = 'vendus.register'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Register'
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    title = fields.Char()
    subscription_active = fields.Boolean()
    status = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id' : response['id'],
            'title'     : response['title'],
            'status'    : response['status'] == 'on',
            'company_id': self.env.company.id
        }

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'registers/'
