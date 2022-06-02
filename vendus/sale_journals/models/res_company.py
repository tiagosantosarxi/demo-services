from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        """ Adds sale order journals to newly created company."""
        company = super(ResCompany, self).create(vals)
        for sale_type in self.env['sale.order.type'].search([]):
            vals = {
                'name'        : sale_type.name,
                'prefix'      : '',
                'sale_type_id': sale_type.id,
                'company_id'  : company.id,
            }
            self.env['sale.order.journal'].sudo().create(vals)
        return company
