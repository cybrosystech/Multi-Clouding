from odoo import models,fields
from collections import defaultdict


def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res

class AccountJournalInherit(models.Model):
    _inherit = "account.journal"

    def _get_journal_dashboard_data_batched(self):
        res = super(AccountJournalInherit, self)._get_journal_dashboard_data_batched()
        self._fill_lease_dashboard_data(res)
        return res

    def _fill_lease_dashboard_data(self,dashboard_data):
        move_fields_list = [
            " (CASE WHEN account_move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * account_move.amount_total AS amount_total",
            "(CASE WHEN account_move.move_type IN ('in_invoice', 'in_refund', 'in_receipt') THEN -1 ELSE 1 END) * account_move.amount_residual_signed AS amount_total_company",
            "account_move.currency_id AS currency",
            "account_move.move_type",
            "account_move.invoice_date",
            "account_move.company_id",
        ]

        bill_query, bill_params = self._get_move_to_approve_query().select(*move_fields_list)
        self.env.cr.execute(bill_query, bill_params)
        query_results_bill_to_approve = self.env.cr.dictfetchall()
        # journal_query, journal_params = self._get_journal_entry_to_approve_query().select(*move_fields_list)
        # self.env.cr.execute(journal_query, journal_params)
        # query_results_journal_to_approve = self.env.cr.dictfetchall()
        ifrs_journals = self.filtered(lambda journal: journal.name.lower().find('ifrs') == 0)
        if not ifrs_journals:
            return

        lease_field_list = [
            " leasee_contract.leasee_currency_id as currency",
            "(CASE WHEN leasee_contract.original_rou!=0 THEN leasee_contract.original_rou ELSE 0 END) as amount_total",
            "(CASE WHEN leasee_contract.original_rou!=0 THEN leasee_contract.original_rou ELSE 0 END) as amount_total_company",
            "leasee_contract.company_id",
        ]

        for journal in self:
            lease_drafts = 0
            lease_drafts_amount = 0
            lease_active = 0
            lease_active_amount = 0
            lease_extended = 0
            lease_extended_amount = 0
            lease_expired = 0
            lease_expired_amount = 0
            lease_terminated = 0
            lease_terminated_amount = 0
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            if journal.name.lower().find('ifrs') == 0:
                query, params = journal._get_lease_draft_query().select(*lease_field_list)
                self.env.cr.execute(query, params)
                query_results_drafts = self.env.cr.dictfetchall()
                query_active, params_active = journal._get_lease_active_query().select(*lease_field_list)
                self.env.cr.execute(query_active, params_active)
                query_results_active = self.env.cr.dictfetchall()

                query_extended, params_extended = journal._get_lease_extended_query().select(*lease_field_list)
                self.env.cr.execute(query_extended, params_extended)
                query_results_extended = self.env.cr.dictfetchall()

                query_expired, params_expired = journal._get_lease_expired_query().select(*lease_field_list)
                self.env.cr.execute(query_expired, params_expired)
                query_results_expired = self.env.cr.dictfetchall()

                query_terminated, params_terminated = journal._get_lease_terminated_query().select(
                    *lease_field_list)
                self.env.cr.execute(query_terminated, params_terminated)
                query_results_terminated = self.env.cr.dictfetchall()

            journal_query, journal_params = journal._get_journal_entry_to_approve_query().select(*move_fields_list)
            self.env.cr.execute(journal_query, journal_params)
            query_results_journal_to_approve = self.env.cr.dictfetchall()

            (number_to_approve, sum_to_approve) = journal._count_results_and_sum_amounts(query_results_bill_to_approve, currency)
            (journal_to_approve, journal_sum_to_approve) = journal._count_results_and_sum_amounts(query_results_journal_to_approve,
                                                                                      currency)
            if journal.name.lower().find('ifrs') == 0:
                (lease_drafts, lease_drafts_amount) = journal._count_results_and_sum_amounts(query_results_drafts, currency)
                (lease_active,lease_active_amount) = journal._count_results_and_sum_amounts(query_results_active, currency)
                (lease_extended, lease_extended_amount) = journal._count_results_and_sum_amounts(query_results_extended, currency)
                (lease_expired, lease_expired_amount) = journal._count_results_and_sum_amounts(query_results_expired,
                                                                                              currency)
                (lease_terminated, lease_terminated_amount) = journal._count_results_and_sum_amounts(query_results_terminated,
                                                                                              currency)
            dashboard_data[journal.id].update({
                'number_to_approve': number_to_approve,
                'sum_to_approve': round(sum_to_approve, 2),
                'journals_to_approve': journal_to_approve,
                'journal_sum_to_approve': round(journal_sum_to_approve, 2),
                'lease_drafts': lease_drafts,
                'lease_drafts_amount':round(lease_drafts_amount,2),
                "lease_active": lease_active,
                "lease_active_amount": round(lease_active_amount,2)     ,
                'lease_extended': lease_extended,
                'lease_extended_amount': round(lease_extended_amount,2),
                'lease_expired': lease_expired,
                'lease_expired_amount':round(lease_expired_amount,2),
                'lease_terminated': lease_terminated,
                'lease_terminated_amount': round(lease_terminated_amount,2),
            })

    def _get_move_to_approve_query(self):
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('state', '=', 'to_approve'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', self.env['account.move'].get_invoice_types(include_receipts=True)),
        ])

    def _get_journal_entry_to_approve_query(self):
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('state', '=', 'to_approve')
        ])

    def _get_lease_draft_query(self):
        return self.env['leasee.contract']._where_calc([
            *self.env['leasee.contract']._check_company_domain(self.env.companies),
            ('state', '=', 'draft'),'|',('initial_journal_id','in',self.ids),('installment_journal_id','in',self.ids)
        ])

    def _get_lease_active_query(self):
        return self.env['leasee.contract']._where_calc([
            *self.env['leasee.contract']._check_company_domain(self.env.companies),
            ('state', '=', 'active'),'|',('initial_journal_id','in',self.ids),('installment_journal_id','in',self.ids)
        ])

    def _get_lease_extended_query(self):
        return self.env['leasee.contract']._where_calc([
            *self.env['leasee.contract']._check_company_domain(self.env.companies),
            ('state', '=', 'extended'),'|',('initial_journal_id','in',self.ids),('installment_journal_id','in',self.ids)
        ])

    def _get_lease_expired_query(self):
        return self.env['leasee.contract']._where_calc([
            *self.env['leasee.contract']._check_company_domain(self.env.companies),
            ('state', '=', 'expired'),'|',('initial_journal_id','in',self.ids),('installment_journal_id','in',self.ids)
        ])

    def _get_lease_terminated_query(self):
        return self.env['leasee.contract']._where_calc([
            *self.env['leasee.contract']._check_company_domain(self.env.companies),
            ('state', '=', 'terminated'),'|',('initial_journal_id','in',self.ids),('installment_journal_id','in',self.ids)
        ])

    def open_journal_entry_to_approve(self):
        """Action window opened to show the to_approve status"""
        action = self.env["ir.actions.act_window"]._for_xml_id(
            'vendor_bills_dashboard.action_move_journal_to_approve')
        action['context'] = ({
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
        })
        action['domain'] = [('state', '=', 'to_approve')]
        return action

    def open_leasee_contract(self):
        """Lease contract open action"""
        action = self.env["ir.actions.act_window"]._for_xml_id(
            'lease_management.view_leasee_contract_action')
        action['domain'] = [('state', '=', self._context['domain'])]
        return action
