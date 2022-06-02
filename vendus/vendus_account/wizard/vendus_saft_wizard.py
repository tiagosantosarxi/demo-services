from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class VendusSaftWizard(models.TransientModel):
    _name = 'vendus.saft.wizard'
    _inherit = 'vendus.mixin'
    _description = 'Vendus SAF-T Wizard'

    def _get_years(self):
        return [(str(i), i) for i in range(fields.Date.today().year, 2017, -1)]

    month = fields.Selection(
        MONTH_SELECTION, default=lambda x: str((fields.Date.today() - relativedelta(months=1)).month), required=True
    )
    year = fields.Selection(selection='_get_years', required=True, default=lambda x: str(fields.Date.today().year))
    filename = fields.Char(readonly=True)
    data = fields.Binary('File', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get'), ('error', 'error')], default='choose')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)

    def execute(self):
        """ Execute is called from the view and calls on a specific route to download the xml
        :rtype: dict to generate the xml file
        """
        if not self.company_id.vendus_api_key:
            raise UserError(_("You cannot generate a SAF-T PT document for a non-portuguese company"))

        # Create the document
        response = self.vendus_list()
        # document = base64.b64encode(document.encode('Windows-1252'))
        # doc_name = "SAF-T-PT_%s_%s_%s_%s.xml" % (self.company_id.vat, self.date_start, self.date_end, VERSION)

        vals = {
            'data': response['xml'],
            'filename': f'SAFT_PT_{self.company_id.vat}_{self.year}_{self.month}.xml',
            'state': 'get'
        }
        self.sudo().write(vals)

        return {
            'type'     : 'ir.actions.act_window',
            'res_model': 'vendus.saft.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id'   : self.id,
            'views'    : [(False, 'form')],
            'target'   : 'new',
        }

    @api.model
    def _get_endpoint_url(self):
        return 'taxauthority/saft/'

    def prepare_list_params(self):
        return {
            'year' : int(self.year),
            'month': int(self.month)
        }

    @api.model
    def vendus_list(self):
        response = self.vendus_request('get', self._get_endpoint_url(), params=self.prepare_list_params() or {})
        return response
