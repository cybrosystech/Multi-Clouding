from ast import literal_eval

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # expense_journal_id = fields.Many2one('account.journal',
    #                                      string="Journal",
    #                                      domain="[('company_id', '=', company_id)]",
    #                                      config_parameter='dev_hr_expense_portal.expense_journal_id',
    #                                      help="Select a journal to be used in "
    #                                           "expense report creation.")

    expense_journal_ids = fields.Many2many('account.journal',
                                         string="Journal",
                                         help="Select a journal to be used in "
                                              "expense report creation.")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        expense_journal_ids = self.env['ir.config_parameter'].sudo().get_param(
            'dev_hr_expense_portal.expense_journal_ids')
        if expense_journal_ids:
            res.update({
                'expense_journal_ids': [(6, 0, literal_eval(
                    expense_journal_ids) if expense_journal_ids else False)]
            })
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'dev_hr_expense_portal.expense_journal_ids',
            self.expense_journal_ids.ids or False)
        return res



    #
    # @api.model
    # def set_values(self):
    #     """employee setting field values"""
    #     res = super(ResConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].set_param(
    #         'expense_journal_ids', self.expense_journal_ids.ids)
    #     return res
    #
    # @api.model
    # def get_values(self):
    #     """employee limit getting field values"""
    #     res = super(ResConfigSettings, self).get_values()
    #     value = self.env['ir.config_parameter'].sudo().get_param(
    #         'expense_journal_ids',False)
    #     print("value",value,type(value))
    #     res.update(
    #         expense_journal_ids=[(6, 0, literal_eval(value))
    #                              ] if value else False,
    #     )
    #     print("____",res)
    #     return res
