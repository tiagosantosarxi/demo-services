import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'
    _name = 'pos.session'

    def open_frontend_cb(self):
        """
        Open POS in Vendus
        """
        pos_config = self.env['pos.config'].search([('id', '=', self.config_id.id)])
        if pos_config.vendus_register_id:
            return {
                'type': 'ir.actions.act_url',
                'url': pos_config.company_id.vendus_url + '/app/pos/',
                'target': 'self',
            }
        return super(PosSession, self).open_frontend_cb()

    def action_pos_session_closing_control(self):
        """
        Invoice Orders
        Call POS session close
        :return: data of order line
        """
        orders = self.env['pos.order'].search([('session_id', '=', self.id)])
        for order in orders:
            if order.state != 'paid' or order.state != 'invoiced' or order.state != 'done':
                order.action_pos_order_invoice()
                invoice = self.env['account.move'].search([('pos_order_ids', '=', order.id)])
                invoice.create_and_add_pdf(order)

        if 'no_cron_call' not in self.env.context:
            self.sudo().env['pos.order'].with_context(SUPERUSER_ID=True)._cron_pos_order_import()
        super(PosSession, self).action_pos_session_closing_control()
