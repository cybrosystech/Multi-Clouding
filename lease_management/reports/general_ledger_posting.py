# -*- coding: utf-8 -*-
""" init object """
import base64
import io
from io import BytesIO,StringIO
from odoo import api,fields, models, _
from datetime import datetime , date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools.misc import get_lang
from odoo.fields import Datetime as fieldsDatetime
import calendar
import csv



class GeneralLedgerPostingWizard(models.TransientModel):
    _name = 'general.ledger.posting.wizard'
    _description = 'General Ledger Posting Wizard'

    def _get_date_from_now(self):
            today=datetime.now().today()
            first_day_this_month = date(day=1, month=today.month, year=today.year)
            return first_day_this_month

    def _get_date_to(self):
        today = datetime.now().today()
        last_day = calendar.monthrange(today.year,today.month)
        last_day_this_month = date(day=last_day[1], month=today.month, year=today.year)
        return last_day_this_month

    date_from = fields.Date(string="Date From",default=_get_date_from_now , required=True, )
    date_to = fields.Date(string="Date To",default=_get_date_to , required=True, )
    account_ids = fields.Many2many(comodel_name="account.account",required=True,
                                   default=lambda self: self._default_accounts())
    leasee_contract_ids = fields.Many2many(comodel_name="leasee.contract", domain=[('parent_id', '=', False)] )
    analytic_account_ids = fields.Many2many(comodel_name="account.analytic.account", )
    is_posted = fields.Boolean(string="Show Posted Entries Only ?", default=False  )
    excel_sheet = fields.Binary('Download Report')
    excel_sheet_name = fields.Char(string='Name', size=64)

    @api.model
    def _default_accounts(self):
        """Fetch default accounts based on account codes."""
        account_codes = ['214201', '224201','122201','122302','581201','554101','211109']  # Replace with the required account codes
        return self.env['account.account'].search([('code', 'in', account_codes)]).ids

    def get_report_data(self):
        date_format = get_lang(self.env).date_format
        ############################################3

        params = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.env.company.id,
        }

        query = """
            SELECT 
                TO_CHAR(am.posting_date, 'YYYY-MM-DD') AS posting_date,
                TO_CHAR(am.date, 'YYYY-MM-DD') AS acc_date,
                TO_CHAR(COALESCE(am.invoice_date, am.date), 'YYYY-MM-DD') AS inv_date,
                am.name AS document_no,
                a.code AS account_number,
                COALESCE(a.name ->> 'en_US', '') AS account_name,
                COALESCE(SPLIT_PART(aml.name, ':', 1), p.name::TEXT, '') AS description,
                aml.amount_currency AS amount,
                COALESCE(lc.name, SPLIT_PART(aml.name, ':', 1), '') AS lease_no,
                lc.state AS lease_state,
                am.state AS move_state,
                am.dimension AS lease_type,
                COALESCE(aa.name ->> 'en_US', '') AS dimension_1,
                COALESCE(ps.name ->> 'en_US', '') AS dimension_2,
                c.name AS company_name,
                aml.debit,
                aml.credit,
                cur.name AS Currency
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN account_account a ON aml.account_id = a.id
            LEFT JOIN product_template p ON aml.product_id = p.id
            LEFT JOIN (
                SELECT * FROM leasee_contract
            ) lc ON lc.id = am.leasee_contract_id
                       OR lc.electricity_id = am.lease_electricity_id
                       OR lc.security_advance_id = am.lease_security_advance_id
            LEFT JOIN account_analytic_account aa ON aml.analytic_account_id = aa.id
            LEFT JOIN account_analytic_account ps ON aml.project_site_id = ps.id
            LEFT JOIN res_company c ON am.company_id = c.id
            LEFT JOIN res_currency cur ON aml.currency_id = cur.id
            WHERE am.date BETWEEN %(date_from)s AND %(date_to)s AND (lc.company_id = %(company_id)s  OR lc.company_id IS NULL)
            """

        params['download_datetime'] = fieldsDatetime.now().strftime(DTF)

        # Filter for posted journal entries
        if self.is_posted:
            query += " AND am.state = 'posted'"

        # Filter for specific account_ids
        if self.account_ids:
            query += " AND aml.account_id = ANY(%(account_ids)s)"
            params['account_ids'] = self.account_ids.ids  # Direct list, PostgreSQL supports `ANY()`

        # Filter for analytic accounts
        if self.analytic_account_ids:
            query += " AND aml.analytic_account_id = ANY(%(analytic_ids)s)"
            params['analytic_ids'] = self.analytic_account_ids.ids

        # Efficiently fetch child leasee contracts and asset IDs via subqueries
        if self.leasee_contract_ids:
            leasee_contract_ids = self.env['leasee.contract'].search([
                ('id', 'child_of', self.leasee_contract_ids.ids)
            ]).ids

            asset_ids = self.env['account.asset'].search([
                ('id', 'child_of', self.leasee_contract_ids.mapped('asset_id').ids)
            ]).ids

            if leasee_contract_ids or asset_ids:
                query += " AND ("

                if leasee_contract_ids:
                    query += " am.leasee_contract_id = ANY(%(leasee_contract_ids)s)"
                    params['leasee_contract_ids'] = leasee_contract_ids

                if leasee_contract_ids and asset_ids:
                    query += " OR "

                if asset_ids:
                    query += " am.asset_id = ANY(%(asset_ids)s)"
                    params['asset_ids'] = asset_ids

                query += ")"

        # Sorting for better performance
        query += " ORDER BY aml.account_id"
        # Execute the query
        # self.env.cr.execute(query, params)
        # res = self.env.cr.dictfetchall()
        # return res
        return query,params

    def print_report_xlsx(self):
        query, params = self.get_report_data()
        self.env.cr.execute(query, params)
        # headers = list(report_data[0].keys())
        headers = [desc.name for desc in self.env.cr.description]

        # Use StringIO for text buffer
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=headers)
        writer.writeheader()
        # writer.writerows(report_data)

        while True:
            row = self.env.cr.fetchone()
            if not row:
                break
            row_dict = dict(zip(headers, row))
            writer.writerow(row_dict)


        # Encode the string data to bytes
        csv_data = csv_buffer.getvalue().encode('utf-8')
        csv_buffer.close()

        # Encode the data to base64 for Odoo binary field
        self.excel_sheet = base64.b64encode(csv_data)
        self.excel_sheet_name = 'general_ledger_posting_report.csv'
        attachment = self.env['ir.attachment'].create({
            'name': self.excel_sheet_name,
            'type': 'binary',
            'datas': base64.b64encode(csv_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/csv'
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
        }
