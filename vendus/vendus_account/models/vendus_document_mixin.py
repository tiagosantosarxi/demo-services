from odoo import api, fields, models


class VendusDocumentMixin(models.AbstractModel):
    _name = 'vendus.document.mixin'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Document Mixin'

    vendus_attachment_id = fields.Many2one('ir.attachment', string="Vendus PDF", required=False, copy=False)
    reason = fields.Char(help="Reason for the status update", size=50, copy=False, readonly=True)

    def create_vendus_pdf(self, binary, name):
        """
        Downloads and creates an attachment for the vendus invoice document
        """

        if not self.vendus_attachment_id:
            doc_name = "".join([name.replace('/', '-'), ".pdf"])

            values = {
                'name'       : doc_name,
                'store_fname': doc_name,
                'res_model'  : self._name,
                'res_id'     : self.id,
                'type'       : 'binary',
                'public'     : True,
                'datas'      : binary,
            }
            self.vendus_attachment_id = self.env['ir.attachment'].sudo().create(values)
        return self.vendus_attachment_id
