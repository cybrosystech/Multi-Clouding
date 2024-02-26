from odoo import models, fields

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    date_of_joining = fields.Date(string="Date of Joining")
    employment_type = fields.Selection(string="Employment Type",
                                       selection=[('FTE', 'FTE'),
                                                  ('Contract', 'Contract'), (
                                                      'consulatncy_agreement',
                                                      'Consultancy Agreement'),
                                                  ('os_ipt', 'OS-IPT'),
                                                  ('os_sim', 'OS-SIM'),
                                                  ('fte_capped', 'FTE-Capped')])
    bank_id = fields.Many2one('res.bank', string='Bank',
                              related='bank_account_id.bank_id')
    bank_bic = fields.Char(related='bank_id.bic', string="SWIFT/BIC")
    branch = fields.Char(string="Branch", related='bank_account_id.branch')
    bank_iban = fields.Char(string="IBAN", related='bank_account_id.bank_iban')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    date_of_joining = fields.Date(string="Date of Joining")
    employment_type = fields.Selection(string="Employment Type",
                                       selection=[('FTE', 'FTE'),
                                                  ('Contract', 'Contract'), (
                                                  'consulatncy_agreement',
                                                  'Consultancy Agreement'),
                                                  ('os_ipt', 'OS-IPT'),
                                                  ('os_sim', 'OS-SIM'),
                                                  ('fte_capped','FTE-Capped')])
    bank_id = fields.Many2one('res.bank', string='Bank',
                              related='bank_account_id.bank_id')
    bank_bic = fields.Char(related='bank_id.bic', string="SWIFT/BIC")
    branch = fields.Char(string="Branch", related='bank_account_id.branch')
    bank_iban = fields.Char(string="IBAN", related='bank_account_id.bank_iban')
