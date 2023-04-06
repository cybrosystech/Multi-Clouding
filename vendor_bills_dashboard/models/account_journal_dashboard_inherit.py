from odoo import models


class AccountJournalInherit(models.Model):
    _inherit = "account.journal"

    def get_journal_dashboard_datas(self):
        """The function is over ride to add extra datas to the journal
        dashboard"""
        res = super(AccountJournalInherit, self).get_journal_dashboard_datas()
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
        currency = self.currency_id or self.company_id.currency_id
        (query, query_args) = self._get_to_approve_bills_query()
        (journal_query, journal_query_args) = self.get_journals_to_approve()
        self.env.cr.execute(query, query_args)
        query_results_to_approve = self.env.cr.dictfetchall()
        self.env.cr.execute(journal_query, journal_query_args)
        journal_query_results_to_approve = self.env.cr.dictfetchall()
        curr_cache = {}
        (number_to_approve,
         sum_to_approve) = self._count_results_and_sum_amounts(
            query_results_to_approve, currency, curr_cache=curr_cache)
        (journal_to_approve,
         journal_sum_to_approve) = self._count_results_and_sum_amounts(
            journal_query_results_to_approve, currency, curr_cache=curr_cache)
        if self.name.lower().find('ifrs') == 0:
            (query, query_args) = self.get_lease_contract_draft()
            self.env.cr.execute(query, query_args)
            query_results_lease_draft = self.env.cr.dictfetchall()
            (lease_drafts, lease_drafts_amount) = self._count_results_and_sum_amounts(query_results_lease_draft, currency,curr_cache=curr_cache)
            (query, query_args) = self.get_lease_contract_active()
            self.env.cr.execute(query, query_args)
            query_results_lease_active = self.env.cr.dictfetchall()
            (lease_active, lease_active_amount) = self._count_results_and_sum_amounts(query_results_lease_active, currency,curr_cache=curr_cache)
            (query, query_args) = self.get_lease_contract_extended()
            self.env.cr.execute(query, query_args)
            query_results_lease_extended = self.env.cr.dictfetchall()
            (lease_extended,
             lease_extended_amount) = self._count_results_and_sum_amounts(
                query_results_lease_extended, currency, curr_cache=curr_cache)
            (query, query_args) = self.get_lease_contract_expired()
            self.env.cr.execute(query, query_args)
            query_results_lease_expired = self.env.cr.dictfetchall()
            (lease_expired,
             lease_expired_amount) = self._count_results_and_sum_amounts(
                query_results_lease_expired, currency, curr_cache=curr_cache)
            (query, query_args) = self.get_lease_contract_terminated()
            self.env.cr.execute(query, query_args)
            query_results_lease_terminated = self.env.cr.dictfetchall()
            (lease_terminated,
             lease_terminated_amount) = self._count_results_and_sum_amounts(
                query_results_lease_terminated, currency, curr_cache=curr_cache)

        res.update({
            'number_to_approve': number_to_approve,
            'sum_to_approve': round(sum_to_approve, 2),
            'journals_to_approve': journal_to_approve,
            'journal_sum_to_approve': round(journal_sum_to_approve, 2),
            'lease_drafts': lease_drafts,
            'lease_drafts_amount': round(lease_drafts_amount, 2),
            'lease_active': lease_active,
            'lease_active_amount': round(lease_active_amount, 2),
            'lease_extended': lease_extended,
            'lease_extended_amount': round(lease_extended_amount, 2),
            'lease_expired': lease_expired,
            'lease_expired_amount': round(lease_expired_amount, 2),
            'lease_terminated': lease_terminated,
            'lease_terminated_amount': round(lease_terminated_amount, 2),
        })
        return res

    def _get_to_approve_bills_query(self):
        """This function is call from the get_journal_dashboard_datas() to
        get the amount and count of to_approve bills"""
        return ('''
                    SELECT
                        (CASE WHEN move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * move.amount_total AS amount_total,
                        move.currency_id AS currency,
                        move.move_type,
                        move.invoice_date,
                        move.company_id
                    FROM account_move move
                    WHERE move.journal_id = %(journal_id)s
                    AND move.state = 'to_approve'
                    AND move.payment_state in ('not_paid', 'partial')
                    AND move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt');
                ''', {'journal_id': self.id})

    def get_journals_to_approve(self):
        """This function is call from the get_journal_dashboard_datas() to
                get the amount and count of to_approve bills"""
        return ('''
                            SELECT
                                (CASE WHEN move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * move.amount_total AS amount_total,
                                move.currency_id AS currency,
                                move.move_type,
                                move.invoice_date,
                                move.company_id
                            FROM account_move move
                            WHERE move.journal_id = %(journal_id)s
                            AND move.state = 'to_approve'
                        ''', {'journal_id': self.id})

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

    def get_lease_contract_draft(self):
        """Lease entries in IFRS jornal """
        return ('''select lease.original_rou as amount_total,
                    lease.leasee_currency_id as currency,
                    lease.company_id
                from leasee_contract lease
                WHERE lease.state = 'draft' 
                and lease.company_id = %(company)s''', {'company': self.env.company.id})

    def get_lease_contract_active(self):
        """Lease entries in IFRS jornal on active state"""
        return ('''select lease.original_rou as amount_total,
                            lease.leasee_currency_id as currency,
                            lease.company_id
                        from leasee_contract lease
                        WHERE lease.state = 'active' 
                        and lease.company_id = %(company)s''',
                {'company': self.env.company.id})

    def get_lease_contract_extended(self):
        """Lease entries in IFRS jornal on extended state"""
        return ('''select lease.original_rou as amount_total,
                                    lease.leasee_currency_id as currency,
                                    lease.company_id
                                from leasee_contract lease
                                WHERE lease.state = 'extended' 
                                and lease.company_id = %(company)s''',
                {'company': self.env.company.id})

    def get_lease_contract_expired(self):
        """Lease entries in IFRS jornal on expired state"""
        return ('''select lease.original_rou as amount_total,
                                            lease.leasee_currency_id as currency,
                                            lease.company_id
                                        from leasee_contract lease
                                        WHERE lease.state = 'expired' 
                                        and lease.company_id = %(company)s''',
                {'company': self.env.company.id})

    def get_lease_contract_terminated(self):
        """Lease entries in IFRS jornal on terminated state"""
        return ('''select lease.original_rou as amount_total,
                                                    lease.leasee_currency_id as currency,
                                                    lease.company_id
                                                from leasee_contract lease
                                                WHERE lease.state = 'terminated' 
                                                and lease.company_id = %(company)s''',
                {'company': self.env.company.id})

    def open_leasee_contract(self):
        """Lease contract open action"""
        action = self.env["ir.actions.act_window"]._for_xml_id(
            'lease_management.view_leasee_contract_action')
        action['domain'] = [('state', '=', self._context['domain'])]
        return action
