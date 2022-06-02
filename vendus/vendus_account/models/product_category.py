import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    vendus_category_id = fields.Many2one('vendus.category', company_dependent=True)

    def search_vendus_category_by_name(self):
        """
        Searches vendus categories by title.
        :return: vendus.category recordset
        """
        return self.env['vendus.category'].search([('title', '=ilike', self.name),
                                                   ('company_id', '=', self.env.company.id)])

    def get_vendus_category(self):
        """
        Returns the linked vendus_id for the category.
        If the category doesn't have a linked vendus_id, searches for a vendus category with the same name and
        updates the category vendus_id field.
        If no vendus category was found, do a create action and return the created vendus_id.
        :return: vendus_id for the matching category
        :rtype: int
        """
        self.ensure_one()
        if self.vendus_category_id:
            return self.vendus_category_id.vendus_id
        categs = self.search_vendus_category_by_name()
        if categs:
            return categs[0].vendus_id
        # Create category block
        vendus_category = self.env['vendus.category'].sudo().create({
            'title' : self.name,
            'status': 'on',
            'company_id': self.env.company.id
        })
        return vendus_category.sudo().vendus_create()['id']

    @api.model
    def search_category_from_vendus_id(self, vendus_id):
        """
        Searches for a category from the vendus_id, creates a new category if none is found.
        :return:
        """
        categ = self.search([('vendus_category_id', '=', vendus_id)], limit=1)
        if not categ:
            vendus_categ = self.env['vendus.category'].search([('vendus_id', '=', vendus_id),
                                                               ('company_id', '=', self.env.company.id)], limit=1)
            if not vendus_categ:
                vendus_categ = vendus_categ.import_single_record_from_vendus(vendus_id)
            categ = self.search([('name', '=', vendus_categ.title)], limit=1)
            if not categ:
                categ = self.create({
                    'name': vendus_categ.title,
                    'parent_id': self.env.ref('product.product_category_all').id
                })
        return categ
