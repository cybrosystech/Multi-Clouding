# -*- coding: utf-8 -*-
""" init object """
import re
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

LOGGER = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS account_move_sequence_index6
            ON public.account_move USING btree
            (journal_id ASC NULLS LAST, id DESC NULLS FIRST, 
            date ASC NULLS FIRST, name COLLATE pg_catalog."default" ASC NULLS LAST)
            TABLESPACE pg_default;
        """)

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get('default_move_journal_types',
                                              ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(
                self._context['default_journal_id'])

            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal()

        return journal

    leasee_contract_id = fields.Many2one(comodel_name="leasee.contract",
                                         index=True)
    leasee_installment_id = fields.Many2one(comodel_name="leasee.installment",
                                            string="", required=False,
                                            index=True)
    leasor_contract_id = fields.Many2one(comodel_name="leasor.contract",
                                         string="", required=False, )
    posting_date = fields.Date()
    is_installment_entry = fields.Boolean(default=False)

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 check_company=True,
                                 domain="[('id', 'in', suitable_journal_ids)]",
                                 default=_get_default_journal, index=True)

    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        if not self.date or not self.journal_id:
            return "WHERE FALSE", {}
        where_string = "WHERE journal_id = %(journal_id)s AND name > '/'"
        param = {'journal_id': self.journal_id.id}
        if not relaxed:
            domain = [('journal_id', '=', self.journal_id.id),
                      ('id', '!=', self.id or self._origin.id),
                      ('name', 'not in', ('/', '', False))]
            if self.journal_id.refund_sequence:
                refund_types = ('out_refund', 'in_refund')
                domain += [('move_type',
                            'in' if self.move_type in refund_types else 'not in',
                            refund_types)]
            reference_move_name = self.search(
                domain + [('date', '<=', self.date)], order='date desc',
                limit=1).name
            if not reference_move_name:
                reference_move_name = self.search(domain, order='date asc',
                                                  limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(
                reference_move_name)
            if sequence_number_reset == 'year':
                where_string += " AND date >= date_trunc('year', %(date)s) AND  date < date_trunc('year', %(date)s) + INTERVAL '1 year' "
                param['date'] = self.date
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:",
                                             self._sequence_monthly_regex.split(
                                                 '(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'month':
                where_string += " AND date >= date_trunc('month', %(date)s) AND  date < date_trunc('month', %(date)s) + INTERVAL '1 month' "
                param['date'] = self.date
            else:
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:",
                                             self._sequence_yearly_regex.split(
                                                 '(?P<seq>')[0]) + '$'
            if param.get(
                    'anti_regex') and not self.journal_id.sequence_override_regex:
                where_string += " AND sequence_prefix !~ %(anti_regex)s "
        if self.journal_id.refund_sequence:
            if self.move_type in ('out_refund', 'in_refund'):
                where_string += " AND move_type IN ('out_refund', 'in_refund') "
            else:
                where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
        return where_string, param

    def _move_autocomplete_invoice_lines_values(self):
        ''' This method recomputes dynamic lines on the current journal entry that include taxes, cash rounding
        and payment terms lines.
        '''
        self.ensure_one()
        for line in self.line_ids.filtered(lambda l: not l.display_type):
            analytic_account = line._cache.get('analytic_account_id')
            # Do something only on invoice lines.
            if line.exclude_from_invoice_tab:
                continue
            # Shortcut to load the demo data.
            # Doing line.account_id triggers a default_get(['account_id']) that could returns a result.
            # A section / note must not have an account_id set.
            if not line._cache.get('account_id') and not line._origin:
                line.account_id = line._get_computed_account() or self.journal_id.default_account_id
            if line.product_id and not line._cache.get('name'):
                line.name = line._get_computed_name()
            # Compute the account before the partner_id
            # In case account_followup is installed
            # Setting the partner will get the account_id in cache
            # If the account_id is not in cache, it will trigger the default value
            # Which is wrong in some case
            # It's better to set the account_id before the partner_id
            # Ensure related fields are well copied.
            if line.partner_id != self.partner_id.commercial_partner_id:
                line.partner_id = self.partner_id.commercial_partner_id
            line.date = self.date
            line.recompute_tax_line = True
            line.currency_id = self.currency_id
            if analytic_account:
                line.analytic_account_id = analytic_account
        if self.env.context.get('lease_contract',
                                False) and self.move_type != 'in_invoice':
            pass
        else:
            self.line_ids._onchange_price_subtotal()
            self._recompute_dynamic_lines(recompute_all_taxes=True)
        values = self._convert_to_write(self._cache)
        values.pop('invoice_line_ids', None)
        return values

    def _post(self, soft=True):
        to_post = super(AccountMove, self)._post(soft)
        for move in to_post:
            move.posting_date = fields.Date.today()
        return to_post
