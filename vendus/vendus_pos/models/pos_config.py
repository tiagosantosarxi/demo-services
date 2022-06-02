import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    vendus_register_id = fields.Many2one('vendus.register')

    def open_ui(self):
        if self.invoice_journal_id.vendus_register_id:
            account = self.env['vendus.account'].search([])
            if not account:
                self.env['vendus.account'].import_all_records_from_vendus()
                account = self.env['vendus.account'].search([], limit=1)
            return {
                'type': 'ir.actions.act_url',
                'url': account.url + '/app/pos/',
                'target': 'new',
            }
        return super(PosConfig, self).open_ui()
