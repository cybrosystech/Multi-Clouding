from odoo import models, fields


class AccountBalanceReportWizard(models.TransientModel):
    _name = 'account.ic.balance.report.wizard'
    _description = 'Account Ending Balance Report'

    company_id = fields.Many2one('res.company', string="Company", required=True,
                                 default=lambda self: self.env.company)
    account_ids = fields.Many2many('account.account', string="Accounts",
                                   domain="[('company_id', '=', company_id)]",
                                   required=True)
    ending_balance_date = fields.Date(string="Ending Balance Date",
                                      default=lambda
                                          self: fields.Datetime.now().date(),
                                      required=True)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id')

    def generate_pdf_report(self):
        docids = self.env['account.account'].search(
            [('id', 'in', self.account_ids.ids)])
        data = {
            'company': self.company_id,
            'account_ids': self.account_ids.ids,
            'ending_balance_date': self.ending_balance_date,
            'currency': self.currency_id.name,
        }
        return self.env.ref(
            'tasc_ic_report.action_account_balance_reports_pdf').report_action(
            docids, data=data)
