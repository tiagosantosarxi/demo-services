from . import models
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _add_sale_order_journals(env)


def _add_sale_order_journals(env):
    """ Adds sale order journal for existing sale order sequences and new journals for new sale document types"""
    for company_id in env['res.company'].search([]):
        for seq in env['ir.sequence'].search(
                [('code', '=', 'sale.order'), '|', ('company_id', '=', company_id.id), ('company_id', '=', False)]):
            if not env['sale.order.journal'].search_count([('sequence_id', '=', seq.id)]):
                vals = {
                    'name'       : env['sale.order.type'].search([('code', '=', 'OR')], limit=1).name + ' - SO',
                    'sequence_id': seq.id,
                    'prefix'     : 'SO',
                    'company_id' : company_id.id
                }

                env['sale.order.journal'].create(vals)

        # Adds sale journals for the new sale types
        for sale_type in env['sale.order.type'].search([]):
            if not env['ir.sequence'].search_count(
                    [('prefix', 'ilike', sale_type.code), ('company_id', '=', company_id.id)]):
                vals = {
                    'name'        : sale_type.name,
                    'prefix'      : '',
                    'sale_type_id': sale_type.id,
                    'company_id'  : company_id.id,
                }
                env['sale.order.journal'].create(vals)

        # Adds all existing sales to the default company journal
        journal = env['sale.order.journal'].search([('company_id', '=', company_id.id),
                                                    ('prefix', '=', 'SO')], limit=1)
        env['sale.order'].search([('company_id', '=', company_id.id)]).write({'journal_id': journal.id})
