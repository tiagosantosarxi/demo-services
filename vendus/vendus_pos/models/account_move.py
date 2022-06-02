import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'vendus.mixin']

    @api.model
    def vendus_list_pdf(self, order_vendus_id):
        return self.vendus_request('get', self._get_endpoint_url() + str(order_vendus_id) + '.pdf',
                                   params=self.prepare_read_params())

    def create_pdf(self, binary, name):
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
        attachment = self.env['ir.attachment'].sudo().create(values)
        return attachment

    def create_and_add_pdf(self, order):
        pdf_doc = self.vendus_list_pdf(order.vendus_id)
        self.create_vendus_pdf(pdf_doc, order.name)
        if order.related_id:
            receipt_pdf_doc = self.vendus_list_pdf(order.related_id)
            self.create_pdf(receipt_pdf_doc, order.name.replace('FT', 'RG'))
