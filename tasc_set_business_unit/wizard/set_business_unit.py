from datetime import datetime, date
from odoo import models, fields, api


class SetBusinessUnit(models.Model):
    _name = 'set.business.unit'

    def _get_date_from_now(self):
        today = datetime.now().today()
        first_day_this_month = date(day=1, month=today.month, year=today.year)
        return first_day_this_month

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string="Date From", default=_get_date_from_now,
                            required=True, )
    date_to = fields.Date(string="Date To", default=_get_date_from_now,
                          required=True, )
    records = fields.Integer(string="Records")
    limit = fields.Integer(string="Limit", required=True)
    business_unit_id = fields.Many2one(comodel_name="account.analytic.account",
                                       domain="[('plan_id.name', '=ilike', 'Business Unit'),'|',('company_id','=',company_id),('company_id','=',False)]",
                                       string="Business Unit",
                                       required=True)
    journal_ids = fields.Many2many('account.journal', string="Journal",
                                 domain="['|',('company_id','=',company_id),('company_id','=',False)]")
    is_update_blank_only = fields.Boolean(string="Update blanks only",help="Enable to update only blanked ones")


    def split_list(self, lst, limit):
        return [lst[i:i + limit] for i in range(0, len(lst), limit)]

    def create_jobs(self, sublist):
        for i in sublist:
            self.with_delay(priority=5)._process_job(i)

    def _process_job(self, iteration):
        # Process the job
        # Perform your task here
        items = iteration
        for item in items:
            item.business_unit_id = self.business_unit_id.id
            item.onchange_project_site()
            analytic_line = self.env['account.analytic.line'].search(
                [('move_line_id', '=', item.id)])
            analytic_line.business_unit_id = self.business_unit_id.id

    def set_business_unit(self):
        domain = []
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.is_update_blank_only:
            domain.append(('business_unit_id', '=', False))

        domain.append(('company_id', '=', self.company_id.id))

        items = self.env['account.move.line'].search(domain, limit=self.limit)

        my_list = items
        sublists = self.split_list(my_list, 250)
        self.create_jobs(sublists)

    @api.onchange('company_id', 'journal_ids', 'date_from', 'date_to','is_update_blank_only')
    def onchange_journal_id(self):
        domain = []
        domain.append(('company_id', '=', self.company_id.id))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.is_update_blank_only:
            domain.append(('business_unit_id', '=', False))

        items_count = self.env['account.move.line'].search_count(domain)
        self.records = items_count
