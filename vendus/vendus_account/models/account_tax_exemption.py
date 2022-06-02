from odoo import api, fields, models
from odoo.osv import expression


class AccountTaxExemption(models.Model):
    _name = 'account.tax.exemption'
    _description = 'Tax Exemption'
    _order = 'display_name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    country_id = fields.Many2one('res.country', required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[%s] %s' % (rec.code, rec.name)

    def name_get(self):
        return [(r.id, r.display_name) for r in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('display_name', operator, name)]
        ids = self._search(expression.AND([domain, args]), limit=limit)
        return self.browse(ids).name_get()
