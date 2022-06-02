from odoo import fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'

    vendus_uom_id = fields.Many2one('vendus.uom', company_dependent=True)

    def search_vendus_uom_by_name(self):
        """
        Searches vendus uom by title.
        :return: vendus.uom recordset
        """
        return self.env['vendus.uom'].search([('title', '=ilike', self.name)])

    def get_vendus_uom(self):
        """
        Returns the linked vendus_id for the uom.
        If the uom doesn't have a linked vendus_id uses the default vendus uom.
        :return: vendus_id for the matching uom
        :rtype: int
        """
        self.ensure_one()
        if self.vendus_uom_id:
            return self.vendus_uom_id.vendus_id
        return self.env['vendus.uom'].search([('default', '=', True)], limit=1).vendus_id
