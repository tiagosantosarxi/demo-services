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
    _inherit = 'vendus.payment.method'

    default_payment_journal_id = fields.Many2one('account.journal')
    payment_method_id = fields.Many2one('pos.payment.method')
