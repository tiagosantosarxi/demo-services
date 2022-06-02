import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderJournal(models.Model):
    _name = 'sale.order.journal'
    _description = 'Sale Journal'
    _order = 'sequence, sale_type_id, prefix'
    _check_company_auto = True

    @api.model
    def _default_sale_type(self):
        return self.env['sale.order.type'].search([], limit=1)

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    sequence_id = fields.Many2one('ir.sequence', 'Journal Sequence', check_company=True, required=True, copy=False)
    name = fields.Char('Journal Name', required=True, translate=True)
    prefix = fields.Char(size=8, required=False)
    sale_type_id = fields.Many2one('sale.order.type', 'Sale Type', required=True, default=_default_sale_type)
    sequence_number_next = fields.Integer('Next Number',
                                          help='The next sequence number will be used for the next order.',
                                          compute='_compute_seq_number_next')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company,
                                 help='Company related to this journal')

    _sql_constraints = [
        ('prefix_company_uniq', 'unique (prefix, sale_type_id, company_id)',
         'The prefix and type of the journal must be unique per company!'),
        ('name_company_uniq', 'unique (name, company_id)',
         'The name of the journal must be unique per company!'),
    ]

    @api.model
    def create(self, vals):
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        return super(SaleOrderJournal, self).create(vals)

    def write(self, vals):
        """
        Prevents updating fields for journals with documents
        """
        for rec in self:
            if rec.env['sale.order'].search_count([('journal_id', '=', rec.id)]):
                if vals.get('company_id'):
                    raise ValidationError(
                        _('You cannot change the company of a journal that already contains documents.'))
                if vals.get('prefix'):
                    raise ValidationError(
                        _('You cannot change the prefix of a journal that already contains documents.'))
            if vals.get('prefix'):
                doc_type_id = vals.get('sale_type_id', rec.sale_type_id.id)
                doc_type = rec.env['sale.order.type'].browse(doc_type_id).code
                rec.sequence_id.write({'prefix': rec._get_sequence_prefix(doc_type, vals.get('prefix'))})
        return super(SaleOrderJournal, self).write(vals)

    def unlink(self):
        """
        Prevents deleting journals with documents
        """
        if self.env['sale.order'].search_count([('journal_id', '=', self)]):
            raise ValidationError(_('You cannot perform this action on a journal that contains documents.'))
        return super(SaleOrderJournal, self).unlink()

    @api.model
    def _get_sequence_prefix(self, doc_type, code):
        prefix = code and code.upper() or ''
        return doc_type + ' ' + prefix + '%(range_year)s/'

    @api.model
    def _create_sequence(self, vals):
        doc = self.env['sale.order.type'].browse(vals['sale_type_id']).code
        prefix = self._get_sequence_prefix(doc, vals.get('prefix'))
        seq_name = doc + ' ' + (vals.get('prefix') or '')
        seq = {
            'name'            : _('%s Sequence') % seq_name,
            'implementation'  : 'no_gap',
            'prefix'          : prefix,
            'padding'         : 4,
            'number_increment': 1,
            'use_date_range'  : True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = vals.get('sequence_number_next', 1)
        return seq

    @api.depends('sequence_id.use_date_range', 'sequence_id.number_next_actual')
    def _compute_seq_number_next(self):
        """
        Computes 'sequence_number_next' according to the current sequence in use,
        an ir.sequence or an ir.sequence.date_range.
        """
        for journal in self:
            if journal.sequence_id:
                sequence = journal.sequence_id._get_current_sequence()
                journal.sequence_number_next = sequence.number_next_actual
            else:
                journal.sequence_number_next = 1
