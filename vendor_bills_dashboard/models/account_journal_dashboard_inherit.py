from odoo import models


class AccountJournalInherit(models.Model):
    _inherit = "account.journal"

    def get_journal_dashboard_datas(self):
        res = super(AccountJournalInherit, self).get_journal_dashboard_datas()
        currency = self.currency_id or self.company_id.currency_id
        (query, query_args) = self._get_to_approve_bills_query()
        self.env.cr.execute(query, query_args)
        query_results_to_approve = self.env.cr.dictfetchall()
        curr_cache = {}
        (number_to_approve, sum_to_approve) = self._count_results_and_sum_amounts(query_results_to_approve, currency, curr_cache=curr_cache)
        res.update({
            'number_to_approve': number_to_approve,
            'sum_to_approve': sum_to_approve
        })
        return res

    def _get_to_approve_bills_query(self):
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
