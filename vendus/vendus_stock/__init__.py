import logging

from odoo import SUPERUSER_ID, api
from . import models

_logger = logging.getLogger(__name__)

MOV_TYPES = {
    'GR': 'Guia de Remessa',
    'GD': 'Guia de Devolução',
    'GA': 'Guia de Movimentação de Ativos Fixos Próprios',
    'GT': 'Guia de Transporte'
}


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Creates default pt transport journals for each portuguese company
    for company in env['res.company'].search([('vendus_active', '=', True)]):
        _logger.info("Creating default stock transport journals for each vendus company")
        _logger.info(company)
        for mov_type, mov_descr in MOV_TYPES.items():
            if not env['stock.transport.journal'].search_count(
                    [('company_id', '=', company.id), ('movement_type', '=', mov_type)]):
                res = env['stock.transport.journal'].create({
                    'company_id'   : company.id,
                    'name'         : mov_descr,
                    'movement_type': mov_type,
                    'sequence'     : 10,
                })
                _logger.info(res)
