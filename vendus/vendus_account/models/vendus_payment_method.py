import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)
PAYMENT_TYPES = [
    ('NU', 'Numerário'),
    ('CC', 'Cartão de Crédito'),
    ('CD', 'Cartão de Débito'),
    ('CO', 'Cartão Oferta'),
    ('CS', 'Compensação de Saldos C/C'),
    ('DE', 'Cartão de Pontos'),
    ('TR', 'Ticket Restaurante'),
    ('MB', 'Referência MB'),
    ('OU', 'Outro'),
    ('CH', 'Cheque Bancário'),
    ('LC', 'Letra Comercial'),
    ('TB', 'Transferência Bancária'),
    ('PR', 'Permuta de Bens'),
    ('DNP', 'Pagamento em conta corrente - entre 15 e 90 dias ou numa data específica'),
    ('MBWAY', 'MB WAY'),
    ('ZARPH', 'Zarph'),
    ('ALICE', 'Alice'),
]


class VendusPaymentMethod(models.Model):
    _name = 'vendus.payment.method'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Payment Method'
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    title = fields.Char()
    change = fields.Boolean()
    method_type = fields.Selection(PAYMENT_TYPES, required=True)
    status = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    default_payment_journal_id = fields.Many2one('account.journal')
    payment_method_line_id = fields.Many2one('account.payment.method.line')

    def prepare_update_vendus_record(self):
        return {}

    def prepare_create_vendus_record(self):
        return {
            'title' : self.title,
            'change': int(self.change),
            'type'  : self.method_type,
            'status': self.status and 'on' or 'off'
        }

    @api.model
    def prepare_import_from_vendus(self, response):
        return {
            'vendus_id'  : str(response['id']),
            'title'      : response['title'],
            'change'     : bool(response['change']),
            'method_type': response['type'],
            'status'     : response['status'] == 'on',
            'company_id' : self.env.company.id
        }

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'documents/paymentmethods/'
