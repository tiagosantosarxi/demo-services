import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusUom(models.Model):
    _name = 'vendus.uom'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Uom'
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    title = fields.Char()
    default = fields.Boolean()
    decimal = fields.Integer()
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    def prepare_update_vendus_record(self):
        return {}

    def prepare_create_vendus_record(self):
        return {
            'title'  : self.title,
            'default': self.default and 'on' or 'off',
            'decimal': self.decimal
        }

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id' : str(response['id']),
            'title'     : response['title'],
            'default'   : response['default'] == 'on',
            'decimal'   : response['decimal'],
            'company_id': self.env.company.id
        }

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'products/units/'
