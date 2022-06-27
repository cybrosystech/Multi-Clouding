from odoo import fields, models


class ProfitabilityReportManaged(models.Model):
    _name = "profitability.report.managed"

    lease_anchor_tenant = fields.Many2many('account.account',
                                           'lease_anchor_tenant_managed_rels')

    lease_colo_tenant = fields.Many2many('account.account',
                                         'lease_colo_tenant_managed_rels')

    additional_space_revenue = fields.Many2many('account.account',
                                                'additional_space_revenue_managed_rels')

    bts_revenue = fields.Many2many('account.account',
                                   'bts_revenue_managed_rels')

    active_sharing_fees = fields.Many2many('account.account',
                                           'active_sharing_fees_managed_rels')

    discount = fields.Many2many('account.account',
                                'discount_managed_rels')

    rou_depreciation = fields.Many2many('account.account',
                                        'rou_depreciation_managed_rela')

    fa_depreciation = fields.Many2many('account.account',
                                       'fa_depreciation_managed_rela')

    lease_finance_cost = fields.Many2many('account.account',
                                          'lease_finance_cost_managed_rel')

    site_maintenance_managed = fields.Many2many('account.account',
                                                'site_maintenances_managed')

    site_maintenance_managed_lim = fields.Many2many('account.account',
                                                    'site_maintenance_managed_lims')

    site_rent = fields.Many2many('account.account',
                                 'site_rent_managed_rels')

    security = fields.Many2many('account.account',
                                'security_managed_rels')

    service_level_credits = fields.Many2many('account.account',
                                             'service_level_credits_managed_rels')
