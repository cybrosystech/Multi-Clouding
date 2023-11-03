# -*- coding: utf-8 -*-
{
  "name"                 :  "HR Payroll Multi-Currency Journal",
  'summary'              :  """Allow to create journal entry for payslip with multi currency""",
  "category"             :  "HR",
  "version"              :  "14.0.1.1.0",
  "author"               :  "Abdallah Mohamed",
  "license"              :  "OPL-1",
  "maintainer"           :  "Abdallah Mohammed",
  "website"              :  "https://www.abdalla.work/r/mW1",
  "support"              :  "https://www.abdalla.work/r/mW1",
  "description"          :  """ ODOO HR Payroll Accounting Multi Currency Journal""",
  "depends"              :  [
                             'hr_payroll_account',
                            ],
  "data"                 :  [
                             'views/hr_contract.xml',
                             'views/hr_payslip.xml',
                             'views/hr_payroll_report.xml',
                             'reports/report_payslip.xml',
                            ],
  "images"               :  [
                             'static/description/main_screenshot.png',
                             'static/description/contract.png',
                             'static/description/payslip.png',
                             'static/description/payslip_report.png',
                             'static/description/journal_entry.png',
                             'static/description/journal.png',
                             'static/description/salary_structure.png',
                             ],
  "application"          :  False,
  "installable"          :  True,
  "price"                :  25,
  "currency"             :  "EUR",
  'sequence'             : 1
}
