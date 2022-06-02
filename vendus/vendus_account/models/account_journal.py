from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    vendus_register_id = fields.Many2one('vendus.register')
    vendus_document_type = fields.Selection([
        ('FT', 'Invoice'),
        ('FR', 'Invoice-Receipt'),
        ('FS', 'Simplified Invoice')], default='FT', string='Document Type')
    default_vendus_payment_method_id = fields.Many2one('vendus.payment.method')
    default_vendus_payment_journal_id = fields.Many2one('account.journal')
