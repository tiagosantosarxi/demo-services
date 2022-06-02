import logging


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'vendus.mixin']
    _order = 'date_order asc'

    register_id = fields.Char()
    store_id = fields.Char()
    related_id = fields.Char()

    @api.model
    def state_of_order_vendus(self, state):
        switcher = {
            'N': 'paid',
            'A': 'cancel',
        }
        return switcher.get(state, 'invoiced')

    @api.model
    def prepare_import_from_vendus(self, response):
        """
        Gets details of order and searchs for the necessary parameters to
        create a order assigning values
        :return: str with data
        """
        details = self.vendus_get_details(response['id'])
        register = self.env['vendus.register'].search(
            [('company_id', '=', self.env.company.id), ('vendus_id', '=', str(response['register_id']))], limit=1
        )
        user = self.env['res.users'].search([('vendus_id.vendus_id', '=', details['user_id'])])
        if not user:
            if not self.env['vendus.user'].search([('vendus_id', '=', details['user_id'])]):
                self.env['vendus.user'].import_single_record_from_vendus(details['user_id'])
                self.env.cr.commit()
            raise ValidationError(_('No user found, try to configure the users.'))
        partner = False
        if 'id' in details['client']:
            partner = self.env['res.partner'].search([('vendus_id', '=', details['client']['id'])])
        session = self.verify_and_create_session(response, register, user)
        lines_list = []
        for item in details['items']:
            lines_list.append((0, 0, self.env['pos.order.line'].prepare_import_from_vendus(item, str(response['id']))))
        payments_list = []
        if 'payments' in details:
            for payment in details['payments']:
                payments_list.append((0, 0, self.env['pos.payment'].prepare_import_from_vendus(payment, response['system_time'], str(response['id']))))
        related_doc_id = False
        if details['related_docs'] and 'id' in details['related_docs'][0]:
            related_doc_id = details['related_docs'][0]['id']
        return {
            'vendus_id'    : str(response['id']),
            'user_id'      : user.id,
            'partner_id'   : partner.id if partner else self.env['res.partner'].search([('name', '=', 'Consumidor Final')]).id,
            'pos_reference': response['number'],
            'name'         : '%s/%s' % (register.title, response['number']),
            'company_id'   : self.env.company.id,
            'store_id'     : response['store_id'],
            'config_id'    : self.env['pos.config'].search(
                [('vendus_register_id.vendus_id', '=', register.vendus_id)]),
            'register_id'  : response['register_id'],
            'date_order'   : response['system_time'],
            'session_id'   : session.id,
            'amount_tax'   : float(response['amount_gross']) - float(response['amount_net']),
            'amount_total' : response['amount_gross'],
            'amount_paid'  : 0.00,
            'amount_return': 0.00,
            'lines'        : lines_list,
            'payment_ids'  : payments_list,
            'related_id'   : related_doc_id,
            'state'        : 'done' if response['type'] == 'FR' else self.state_of_order_vendus(response['status']),
        }

    def prepare_update_vendus_record(self):
        return {
            'status': 'F',
            'mode'  : self.env.company.vendus_test and 'tests' or 'normal',
        }

    def action_pos_order_invoice(self):
        ctx = dict(self.env.context, vendus_update=True)
        return super(PosOrder, self.with_context(ctx)).action_pos_order_invoice()

    def vendus_get_details(self, vendus_id):
        """
        Prepare API request to get Order details
        :return: str with data
        """
        return self.vendus_request(
            'get', self._get_endpoint_url() + str(vendus_id), params=self.prepare_read_params()
        )

    @api.model
    def vendus_list(self):
        """
        Make API request
        :return: records from the API request
        """
        response = []
        last_update = fields.Datetime.to_datetime(self.env['ir.config_parameter'].sudo().get_param(
            'vendus.last_update', '2020-01-01'
        ))
        vendus_pos_configs = self.env['pos.config'].search([
            ('company_id', '=', self.env.company.id),
            ('invoice_journal_id.vendus_register_id', '!=', False)
        ])
        for pos_config in vendus_pos_configs:
            vals = {
                'type'       : 'FT,FR',
                'register_id': pos_config.vendus_register_id.vendus_id,
                'per_page'   : 1000,
                'page'       : 1,
                'since'      : last_update.date().isoformat(),
            }
            vals.update(self.prepare_read_params())
            response.extend(self.with_context(SUPERUSER_ID=self._context.get('SUPERUSER_ID', True)).vendus_request('get', self._get_endpoint_url(), params=vals))
            response = sorted(response, key=lambda i: i['system_time'])
            _logger.info("RESPONSE: {}".format(response))
        return response

    @api.model
    def prepare_read_params(self):
        return {'mode': self.env.company.vendus_test and 'tests' or 'normal'}

    def prepare_update_from_vendus(self, vendus_record_dict):
        return self.prepare_import_from_vendus(vendus_record_dict)

    @api.model
    def _get_endpoint_url(self):
        return 'documents/'

    @api.model
    def _cron_pos_order_import(self):
        self.with_context(SUPERUSER_ID=True).import_all_records_from_vendus()
        return True

    def verify_and_create_session(self, response, register, user):
        """
        Verify the user of the current session
        close current session and open new one if needed
        :return: current session or the new session
        """
        config_id = self.env['pos.config'].search(
            [('invoice_journal_id.vendus_register_id.vendus_id', '=', register.vendus_id)], limit=1
        )
        session = self.env['pos.session'].search([('config_id', '=', config_id.id), ('state', '=', 'opened')])
        if session:
            if session.user_id == user:
                return session
            else:
                ctx = dict(self.env.context, no_cron_call=True)
                session.with_context(ctx).action_pos_session_closing_control()

        return self.env['pos.session'].create({
            'config_id': config_id.id,
            'name'     : register.title,
            'state'    : 'opened',
            'start_at' : response['system_time'],
            'user_id'  : user.id,
        })

    @api.model
    def import_all_records_from_vendus(self, override=False):
        """
        Imports all records and returns created and updated stats.
        :param override: If override is True and if there's a already a matching record in Odoo, that record will be
        updated with the vendus data from the API.
        :return:
        """
        response = self.with_context(SUPERUSER_ID=self._context.get('SUPERUSER_ID', True)).vendus_list()
        vals_list = []
        updated = 0
        for vendus_dict in response:
            # Search
            rec = self.search(self.prepare_find_record_by_domain_list(vendus_dict), limit=1)
            if rec and override:
                rec.write(rec.prepare_update_from_vendus(vendus_dict))
                rec.flush()
                updated += 1
            elif not rec:
                vals_list.append(self.prepare_import_from_vendus(vendus_dict))
        # Create
        if vals_list:
            response = self.create(vals_list)
            for order in response:
                if order.state == 'paid' or order.state == 'invoiced' or order.state == 'done':
                    order.action_pos_order_invoice()
                    invoice = self.env['account.move'].search([('pos_order_ids', '=', order.id)])
                    invoice.create_and_add_pdf(order)
        _logger.info(f"Vendus Import: {len(vals_list)} {self._description} created!")
        _logger.info(f"Vendus Import: {updated} {self._description} updated!")
        return len(vals_list), updated

    @api.model
    def _complete_values_from_session(self, session, values):
        if values.get('state') and values['state'] == 'paid' and values['name'] == '':
            values['name'] = session.config_id.sequence_id._next()
        values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        values.setdefault('fiscal_position_id', session.config_id.default_fiscal_position_id.id)
        values.setdefault('company_id', session.config_id.company_id.id)
        return values
