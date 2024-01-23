from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_journal_id = fields.Many2one('account.journal',
                                         string="Journal",
                                         required=True,
                                         config_parameter='dev_hr_expense_portal.expense_journal_id',
                                         help="Select a journal to be used in "
                                              "expense report creation.")

    @api.model
    def set_values(self):
        """employee setting field values"""
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'expense_journal_id', self.expense_journal_id.id)
        return res

    @api.model
    def get_values(self):
        """employee limit getting field values"""
        res = super(ResConfigSettings, self).get_values()
        value = self.env['ir.config_parameter'].sudo().get_param(
            'expense_journal_id',False)
        res.update(
            expense_journal_id=int(value)
        )
        return res
