from odoo import models, fields


class ProfitabilityReportOwned(models.Model):
    _name = 'profitability.report.owned'

    service_revenue = fields.Many2many('account.account',
                                       'service_revenue_owned_rel',
                                       string='Service Revenue')
    investment_revenue = fields.Many2many('account.account',
                                          'investment_revenue_owned_rel',
                                          string='Investment Revenue')
    colocation = fields.Many2many('account.account', 'colocation_owned_rel',
                                  string='Colocation')
    pass_through_energy = fields.Many2many('account.account',
                                           'pass_through_owned_energy',
                                           string='Pass Through Energy')
    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_owned_fees',
                                           string='Active Sharing Fees')
    discount = fields.Many2many('account.account', 'disc_owned',
                                string='Discount')
    site_maintenance = fields.Many2many('account.account',
                                        'site_owned_maintenance')
    site_maintenance_lim = fields.Many2many('account.account',
                                            'site_maintenance_owned_lim')
    insurance = fields.Many2many('account.account', 'insurance_owned_',
                                 string="Insurance")
    energy_cost = fields.Many2many('account.account', 'energy_owned_cost',
                                   string='Energy Cost')
    security = fields.Many2many('account.account', 'security_owned',
                                string='Security')
    service_level_credit = fields.Many2many('account.account',
                                            'service_level_owned_credit',
                                            string='Service Level Credit')
    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_owned_rels',
                                        string='ROU Depreciation')
    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_owned_rel')
    fa_depreciation_lim = fields.Many2many('account.account',
                                           'fa_depreciation_lim_owned_rel',
                                           )
    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_owned_rels',
                                          string='Leases Finance Cost')
