import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class VendusCron(models.Model):
    _name = 'vendus.cron'
    _description = 'Vendus Cron'

    last_update = fields.Datetime(readonly=True)
