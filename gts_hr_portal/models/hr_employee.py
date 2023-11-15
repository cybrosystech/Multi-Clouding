
from odoo import models, api,fields, _
from odoo.tools import email_split
from odoo.exceptions import UserError


def extract_email(email):
    """ extract the email address from a user-friendly email address """
    addresses = email_split(email)
    return addresses[0] if addresses else ''


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', groups="hr.group_hr_user,base.group_portal", default='single', tracking=True)
    children = fields.Integer(string='Number of Children', groups="base.group_portal,hr.group_hr_user", tracking=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_home_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="base.group_portal,hr.group_hr_user",
        tracking=True,
        help='Employee bank salary account')
    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days', 'payslip_id', string='Payslip Worked Days', copy=True,
        compute='_compute_worked_days_line_ids', store=True, readonly=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'paid': [('readonly', True)]})
    identification_id = fields.Char(string='Identification No', groups="base.group_portal,hr.group_hr_user", tracking=True)

    first_contract_date = fields.Date(compute='_compute_first_contract_date', groups="base.group_portal,hr.group_hr_user", store=True)

    contract_id = fields.Many2one(
        'hr.contract', string='Current Contract', groups="base.group_portal,hr.group_hr_user",
        domain="[('company_id', '=', company_id), ('employee_id', '=', id)]", help='Current contract of the employee')

    @api.model
    def create(self, vals):
        employee = super(HrEmployee, self).create(vals)
        if not employee.user_id:
            if not employee.work_email:
                raise UserError(_('Work email is not defined for employee %s !') % employee.name)
            user = employee.sudo()._create_user()
            group_portal = self.env.ref('base.group_portal')
            group_public = self.env.ref('base.group_public')
            user.write({'active': True, 'groups_id': [(4, group_portal.id), (3, group_public.id)]})
            employee.user_id = user.id
        return employee

    def _create_user(self):
        company = self.env.user.company_id
        company = self.company_id or company
        return self.env['res.users'].with_context(no_reset_password=True).sudo()._create_user_from_template({
            'email': extract_email(self.work_email),
            'login': extract_email(self.work_email),
            'name': self.name,
            'partner_id': self.address_home_id and self.address_home_id.id or False,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
        })
