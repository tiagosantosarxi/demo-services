import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = 'vendus.model'
    _description = 'Vendus Model'

    name = fields.Char(required=False)
    n_records = fields.Integer(compute='_compute_n_records')
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', readonly=True)
    relative_endpoint = fields.Char()

    def _compute_n_records(self):
        for rec in self.filtered('model_id'):
            rec.n_records = self.env[rec.model_id.model].search_count([])

    def action_see_records(self):
        self.ensure_one()
        action = {
            'name'     : self.model_id.name,
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': self.model_id.model,
            'res_id'   : self.env[self.model_id.model].search([]).ids
        }
        return action

    def sync(self):
        self.ensure_one()
        self.env[self.model_id.model].import_all_records_from_vendus()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
