import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    exemption_id = fields.Many2one('account.tax.exemption')

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        val.update({
            'exemption_id': self.exemption_id and self.exemption_id.id
        })
        return val


class AccountTax(models.Model):
    _inherit = 'account.tax'

    exemption_id = fields.Many2one('account.tax.exemption')

    def _selection_country_region(self):
        """
        Selection option for the country region (all countries + azores and madeira regions)
        """
        res = [(country.code, country.name) for country in self.env['res.country'].search([])]
        res += [('PT-AC', _('Azores')), ('PT-MA', _('Madeira'))]
        return res

    country_region = fields.Selection(string='Tax Country Region', selection='_selection_country_region')

    def get_vendus_tax_type(self):
        self.ensure_one()
        if self.country_code == 'PT':
            return self.amount == 23 and 'NOR' or self.amount == 13 and 'INT' or self.amount == 6 and 'RED' or 'ISE'
        elif self.country_code == 'PT-AC':
            return self.amount == 18 and 'NOR' or self.amount == 9 and 'INT' or self.amount == 4 and 'RED' or 'ISE'
        elif self.country_code == 'PT-MA':
            return self.amount == 22 and 'NOR' or self.amount == 12 and 'INT' or self.amount == 5 and 'RED' or 'ISE'
        elif self.country_code == 'AO':
            return self.amount == 14 and 'NOR' or self.amount == 5 and 'RED' or 'ISE'
        else:
            return self.amount and 'NOR' or 'ISE'

    @api.model
    def find_tax_by_vendus_id(self, vendus_id, exemption_code):
        domain = [('company_id', '=', self.env.company.id), ('amount', '=', self.vendus_id_2_amount(vendus_id))]
        if vendus_id == 'ISE':
            domain.append(('exemption_id', '=', exemption_code))
        return self.search(domain, limit=1)

    @api.model
    def vendus_id_2_amount(self, vendus_id):
        if self.env.company.country_code == 'PT':
            switcher = {
                'NOR': 23,
                'INT': 13,
                'RED': 6,
                'ISE': 0,
            }
        elif self.env.company.country_code == 'AO':
            switcher = {
                'NOR': 14,
                'INT': 5,
                'RED': 2,
                'ISE': 0,
            }
        else:
            return 0
        return switcher.get(vendus_id)
