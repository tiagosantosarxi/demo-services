from odoo import SUPERUSER_ID, api
from . import models
from . import wizard


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('account.email_template_edi_invoice', raise_if_not_found=False).report_template = env.ref('account.account_invoices_without_payment').id
