from odoo import api, models, fields, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError


class MassAllocation(models.Model):
    _name = 'mass.allocation'
    _description = 'Mass Allocation'

    name = fields.Char(
        string='Name',
        copy=False,
        required=1
    )
    date_from = fields.Date(string="Accounting Date From", required=1)
    date_to = fields.Date(string="Accounting Date To", required=1)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'), ('to_approve', 'To Approve'),
    ], string='Status', required=True, copy=False, tracking=True,
        default='posted')
    business_unit_id = fields.Many2one(comodel_name="account.analytic.account",
                                       domain=[('plan_id.name', '=ilike', 'Business Unit')],
                                       string="Business Unit", required=True, )

    account_ids = fields.Many2many('account.account', string="Account")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    mass_allocation_line_ids = fields.One2many(
        comodel_name="mass.allocation.line",
        inverse_name="mass_allocation_id",
        string="",
        required=False, copy=False)
    mass_allocation_move_id = fields.Many2one('account.move', string="Mass Allocation Entry", copy=False)

    def action_generate_mass_allocation_lines(self):
        if self.mass_allocation_line_ids:
            self.mass_allocation_line_ids = [(5, 0, 0)]
        journal_id = self.env['account.journal'].search(
            [('name', '=ilike', 'Mass Allocation'), ('company_id', '=', self.company_id.id)], limit=1)

        domain = [
            ('company_id', '=', self.company_id.id),
            ('business_unit_id', '=', self.business_unit_id.id),
            ('parent_state', '=', self.state),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', '!=', journal_id.id),
            ('mass_allocation_id', '=', False)
        ]
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))

        move_lines = self.env['account.move.line'].read_group(
            domain=domain,
            fields=['balance', 'business_unit_id', 'account_id'],
            groupby=['business_unit_id', 'account_id'],
            lazy=False
        )
        if not move_lines:
            raise UserError("No data to show.")

        for line in move_lines:
            self.env['mass.allocation.line'].create({
                'mass_allocation_id': self.id,
                'business_unit_id': line['business_unit_id'][0],
                'account_id': line['account_id'][0],
                'balance': line['balance'],
            })

    def view_mass_entry(self):
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": self.mass_allocation_move_id.id,
            "target": 'current'
        }
        return action

    def action_generate_mass_entry(self):
        invoice_lines = []
        journal_id = self.env['account.journal'].search(
            [('name', '=ilike', 'Mass Allocation'), ('company_id', '=', self.company_id.id)], limit=1)

        ########################start##########################
        domain = [
            ('company_id', '=', self.company_id.id),
            ('business_unit_id', '=', self.business_unit_id.id),
            ('parent_state', '=', self.state),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', '!=', journal_id.id),
            ('mass_allocation_id', '=', False)
        ]
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        move_lines = self.env['account.move.line'].read_group(
            domain=domain,
            fields=['balance', 'business_unit_id', 'account_id', 'analytic_account_id', 'project_site_id'],
            groupby=['business_unit_id', 'account_id', 'analytic_account_id', 'project_site_id'],
            lazy=False
        )
        move_lines_to_update = self.env['account.move.line'].search(domain)
        prec = self.company_id.currency_id.decimal_places
        energy_bu = self.env['account.analytic.account'].search(
            [('name', '=ilike', 'Energy'), ('company_id', '=', self.company_id.id),
             ('plan_id.name', '=ilike', 'Business Unit')])
        common_cost_bu = self.env['account.analytic.account'].search(
            [('name', '=ilike', 'Common Costs'), ('company_id', '=', self.company_id.id),
             ('plan_id.name', '=ilike', 'Business Unit')])
        managed_services_bu = self.env['account.analytic.account'].search(
            [('name', '=ilike', 'Managed Services'), ('company_id', '=', self.company_id.id),
             ('plan_id.name', '=ilike', 'Business Unit')])
        real_estate_bu = self.env['account.analytic.account'].search(
            [('name', '=ilike', 'Real Estate'), ('company_id', '=', self.company_id.id),
             ('plan_id.name', '=ilike', 'Business Unit')])

        for rec in self.mass_allocation_line_ids:
            journal_items = [line for line in move_lines if line['account_id'][0] == rec.account_id.id]
            for item in journal_items:
                managed_services_amount = 0
                energy_amount = 0
                real_estate_amount = 0
                common_cost_amount = 0
                if item["balance"] != 0:
                    invoice_lines.append((0, 0, {
                        'business_unit_id': rec.business_unit_id.id,
                        'analytic_account_id': item["analytic_account_id"][0] if item["analytic_account_id"] else False,
                        'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                        'account_id': rec.account_id.id,
                        'debit': item["balance"] if float_compare(item["balance"], 0.0,
                                                                  precision_digits=prec) < 0 else 0.0,
                        'credit': item["balance"] if float_compare(item["balance"], 0.0,
                                                                   precision_digits=prec) > 0 else 0.0,
                    }))

                    if rec.common_cost != 0:
                        common_cost_amount = item["balance"] * (rec.common_cost / 100)
                    if rec.real_estate != 0:
                        real_estate_amount = item["balance"] * (rec.real_estate / 100)
                    if rec.energy != 0:
                        energy_amount = item["balance"] * (rec.energy / 100)
                    if rec.managed_services != 0:
                        managed_services_amount = item["balance"] * (rec.managed_services / 100)
                    if all(val == 0 for val in [rec.common_cost, rec.real_estate, rec.energy, rec.managed_services]):
                        invoice_lines.append((0, 0, {
                            'business_unit_id': False,
                            'analytic_account_id': item["analytic_account_id"][0] if item[
                                "analytic_account_id"] else False,
                            'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                            'account_id': rec.account_id.id,
                            'debit': item["balance"] if float_compare(item["balance"], 0.0,
                                                                      precision_digits=prec) > 0 else 0.0,
                            'credit': item["balance"] if float_compare(item["balance"], 0.0,
                                                                       precision_digits=prec) < 0 else 0.0,
                        }))
                    else:
                        if common_cost_amount != 0:
                            invoice_lines.append((0, 0, {
                                'business_unit_id': common_cost_bu.id,
                                'analytic_account_id': item["analytic_account_id"][0] if item[
                                    "analytic_account_id"] else False,
                                'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                                'account_id': rec.account_id.id,
                                'debit': common_cost_amount if float_compare(common_cost_amount, 0.0,
                                                                             precision_digits=prec) > 0 else 0.0,
                                'credit': common_cost_amount if float_compare(common_cost_amount, 0.0,
                                                                              precision_digits=prec) < 0 else 0.0,
                            }))
                        if real_estate_amount != 0:
                            invoice_lines.append((0, 0, {
                                'business_unit_id': real_estate_bu.id,
                                'analytic_account_id': item["analytic_account_id"][0] if item[
                                    "analytic_account_id"] else False,
                                'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                                'account_id': rec.account_id.id,
                                'debit': real_estate_amount if float_compare(real_estate_amount, 0.0,
                                                                             precision_digits=prec) > 0 else 0.0,
                                'credit': real_estate_amount if float_compare(real_estate_amount, 0.0,
                                                                              precision_digits=prec) < 0 else 0.0,
                            }))
                        if energy_amount != 0:
                            invoice_lines.append((0, 0, {
                                'business_unit_id': energy_bu.id,
                                'analytic_account_id': item["analytic_account_id"][0] if item[
                                    "analytic_account_id"] else False,
                                'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                                'account_id': rec.account_id.id,
                                'debit': energy_amount if float_compare(energy_amount, 0.0,
                                                                        precision_digits=prec) > 0 else 0.0,
                                'credit': energy_amount if float_compare(energy_amount, 0.0,
                                                                         precision_digits=prec) < 0 else 0.0,
                            }))
                        if managed_services_amount != 0:
                            invoice_lines.append((0, 0, {
                                'business_unit_id': managed_services_bu.id,
                                'analytic_account_id': item["analytic_account_id"][0] if item[
                                    "analytic_account_id"] else False,
                                'project_site_id': item["project_site_id"][0] if item["project_site_id"] else False,
                                'account_id': rec.account_id.id,
                                'debit': managed_services_amount if float_compare(managed_services_amount, 0.0,
                                                                                  precision_digits=prec) > 0 else 0.0,
                                'credit': managed_services_amount if float_compare(managed_services_amount, 0.0,
                                                                                   precision_digits=prec) < 0 else 0.0,
                            }))
        invoice = self.env['account.move'].create({
            'move_type': 'entry',
            'currency_id': self.env.company.currency_id.id,
            'ref': self.name if self.name else '',
            'line_ids': invoice_lines,
            'date': self.date_to,
            'journal_id': journal_id.id,
        })
        self.mass_allocation_move_id = invoice.id
        if move_lines_to_update:
            move_lines_to_update.write({'mass_allocation_id': self.id})
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": 'account.move',
            "res_id": invoice.id,
            "target": 'current'
        }
        # self.is_entry_generated = True
        return action


class MassAllocationLine(models.Model):
    _name = 'mass.allocation.line'

    business_unit_id = fields.Many2one(comodel_name="account.analytic.account",
                                       domain=[('plan_id.name', '=ilike', 'Business Unit')],
                                       string="Business Unit", required=False, )
    mass_allocation_id = fields.Many2one('mass.allocation')
    balance = fields.Float(string="Balance")
    account_id = fields.Many2one('account.account', string="Account")
    common_cost = fields.Float(string="Common Cost")
    real_estate = fields.Float(string="Real Estate")
    energy = fields.Float(string="Energy")
    managed_services = fields.Float(string="Managed Services")
    total = fields.Float(string="Total", compute='_compute_total', store=True)

    @api.depends('common_cost', 'real_estate', 'energy', 'managed_services')
    def _compute_total(self):
        for record in self:
            record.total = (
                    record.common_cost +
                    record.real_estate +
                    record.energy +
                    record.managed_services
            )

    @api.constrains('total')
    def _check_total(self):
        for record in self:
            if not any([record.common_cost, record.real_estate, record.energy, record.managed_services]):
                continue
            if not abs(record.total - 100.0) <= 0.001:  # Small tolerance for float precision
                raise ValidationError("The total must always be 100.")
