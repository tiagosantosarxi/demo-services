from odoo import _, models, api
from odoo.exceptions import UserError

CERTIFITED_REPORTS = [
    'account.report_invoice',
    'sale.report_saleorder',
    'sale.report_saleorder_pro_forma',
    'account.report_payment_receipt',
    'vendus_stock.report_transport',
    'account.report_invoice_with_payments'
]

CERTIFIED_MODELS = [
    'account.move',
    'sale.order',
    'account.payment',
    'stock.transport'
]


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None):
        """
        We need to override the render qweb to avoid printing an odoo report if the record has a vendus ID.
        :param res_ids:
        :param data:
        :return:
        """
        self_sudo = self.sudo()
        previous_attachment = self_sudo.attachment
        previous_attachment_use = self_sudo.attachment_use
        if self.model in CERTIFIED_MODELS and not self.env.context.get('force_print'):
            rec_ids = self_sudo.env[self.model].browse(res_ids or [])
            if self.report_name in CERTIFITED_REPORTS:
                if any(rec['state'] == 'draft' for rec in rec_ids):
                    if rec_ids.mapped('company_id.vendus_active'):
                        if len(rec_ids) == 1:
                            raise UserError(_('This record is in a draft state.'))
                        raise UserError(_('This action has one or more draft records.'))
                self_sudo.attachment = True
                self_sudo.attachment_use = True

        res = super(IrActionsReport, self)._render_qweb_pdf(res_ids, data)
        if self.attachment != previous_attachment:
            self_sudo.attachment = previous_attachment
        if self.attachment_use != previous_attachment_use:
            self_sudo.attachment_use = previous_attachment_use
        return res

    def retrieve_attachment(self, record):
        if {'vendus_attachment_id', 'vendus_id'}.issubset(
                set(record._fields)) and record.vendus_id and not record.vendus_attachment_id:
            record.create_vendus_pdf()
        if 'vendus_attachment_id' in record._fields and record['vendus_attachment_id']:
            return record['vendus_attachment_id']
        return super(IrActionsReport, self).retrieve_attachment(record)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        """
        Odoo has no prepare in _postprocess_pdf_report for ir.attachment create
        and does a safe_eval from a Char Field expecting a specific expression.

        We need to str() this expression has it may be in a different type in the end of save_eval due to attachment_use
        in ir.actions.report
        """
        if vals.get('name') and str(vals.get('name')) == 'True' and vals.get('res_model') and vals.get('name'):
            rec = self.env[vals.get('res_model')].browse(vals.get('res_id'))
            vals['name'] = rec and rec.name_get()[0][1] or str(vals.get('name'))
        return super(IrAttachment, self).create(vals)
