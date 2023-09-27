from odoo import api, models


class ReportAccountBalance(models.AbstractModel):
    _name = 'report.tasc_ic_report.report_account_balance'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.account'].browse(data["account_ids"])
        wizard = self.env['account.ic.balance.report.wizard'].browse(
            data['context']['active_id'])
        self._cr.execute(
            'select account.name,account.id,account.code as code,'
            'ABS(coalesce((sum(item.debit) - sum(item.credit)), 0)) as balance '
            'from account_move_line as item inner join account_account as '
            'account on account.id=item.account_id where '
            'item.account_id in %(accounts)s  and '
            'item.date<=%(to_date)s and item.company_id=%(company)s and '
            'item.parent_state=%(state)s group by account.id',
            {'accounts': tuple(docs.ids),
             'to_date': data["ending_balance_date"],
             'company': self.env.company.id,
             'state': 'posted'})
        qry = self._cr.dictfetchall()
        self._cr.execute(
            'select account.name,account.id as account_id,'
            'item.date,journal.name as journal,'
            '(select name as partner_name from res_partner '
            'where id=journal.partner_id),item.name as label,'
            'item.amount_currency as amount_currency ,'
            'item.credit,abs(item.debit) as debit '
            'from account_move_line as item '
            'inner join account_account as account on '
            'account.id=item.account_id'
            ' inner join account_move as journal on journal.id=item.move_id '
            ' where item.account_id in %(accounts)s  '
            'and item.date<=%(to_date)s '
            'and item.company_id=%(company)s and '
            'item.parent_state=%(state)s group by '
            'account.id,journal.id,'
            'item.id',
            {'accounts': tuple(docs.ids),
             'to_date': data["ending_balance_date"],
             'company': self.env.company.id,
             'state': 'posted'})
        qry_all = self._cr.dictfetchall()
        return {
            'doc_ids': docids,
            'doc_model': 'account.account',
            'docs': docs,
            'data': data,
            'res': qry,
            'result': qry_all,
            'cmpny': wizard.company_id,
        }
