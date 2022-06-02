import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class VendusWizard(models.TransientModel):
    _name = 'vendus.wizard'
    _inherit = 'vendus.mixin'
    _description = 'Vendus Wizard'

    state = fields.Selection([('choose', 'Choose'), ('get', 'Get')], default='choose', readonly=True)
    result = fields.Text(readonly=True)
    import_customers = fields.Boolean(default=True)
    import_products = fields.Boolean(default=True)
    import_uoms = fields.Boolean(default=True)
    import_brands = fields.Boolean(default=True)
    import_categories = fields.Boolean(default=True)
    import_pricegroups = fields.Boolean(default=True)
    import_payment_methods = fields.Boolean(default=True)
    import_registers = fields.Boolean(default=True)
    import_employees = fields.Boolean(default=True)
    import_accounts = fields.Boolean(default=True)

    def action_sync_base_info(self):
        """
        Action to sync all info from Vendus.
        :return: page reload
        """
        self.result = ''
        self.sync_model('import_customers', 'res.partner')
        self.sync_model('import_products', 'product.product')
        self.sync_model('import_uoms', 'vendus.uom')
        self.sync_model('import_brands', 'vendus.brand')
        self.sync_model('import_categories', 'vendus.category')
        self.sync_model('import_pricegroups', 'vendus.pricegroup')
        self.sync_model('import_payment_methods', 'vendus.payment.method')
        self.sync_model('import_registers', 'vendus.register')
        self.sync_model('import_employees', 'vendus.user')
        self.sync_model('import_accounts', 'vendus.account')

        self.write({'state': 'get'})
        action = self.env['ir.actions.act_window']._for_xml_id('vendus_account.vendus_wizard_action')
        action['res_id'] = self.id
        return action

    def sync_model(self, field, model):
        if self[field]:
            created, updated = self.env[model].with_context(SUPERUSER_ID=True).import_all_records_from_vendus()
            self.result += f'{created} {self.env[model]._description} created\n'
            self.result += f'{updated} {self.env[model]._description} updated\n'

    def reload(self):
        return {
            'type': 'ir.actions.client',
            'tag' : 'reload',
        }
