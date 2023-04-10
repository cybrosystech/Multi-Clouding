from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    analytic_account_type = fields.Selection(selection_add=[('co_location',
                                                             'Co Location')])
    co_location = fields.Many2one('account.analytic.account',
                                  string="Co location",
                                  domain=[('analytic_account_type', '=',
                                           'co_location')])


class AccountAssetInherit(models.Model):
    _inherit = 'account.asset'

    co_location = fields.Many2one('account.analytic.account',
                                  string="Co location",
                                  domain=[('analytic_account_type', '=',
                                           'co_location')],
                                  required=False)

    @api.onchange('project_site_id')
    def _onchange_project_site_id(self):
        for rec in self:
            rec.co_location = rec.project_site_id.co_location.id
        return super(AccountAssetInherit, self)._onchange_project_site_id()

    @api.depends('acquisition_date', 'original_move_line_ids', 'method_period',
                 'company_id')
    def _compute_first_depreciation_date(self):
        if self.prorata:
            self.prorata_date = self.acquisition_date
        return super(AccountAssetInherit, self)._compute_first_depreciation_date()

    @api.onchange('prorata')
    def _onchange_prorata(self):
        if self.prorata and self.acquisition_date:
            self.prorata_date = self.acquisition_date
        else:
            self.prorata_date = fields.Date.today()


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co location", domain=[(
            'analytic_account_type', '=', 'co_location')], required=False, )

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.co_location_id = rec.project_site_id.co_location.id
        return super(AccountMoveLineInherit, self).get_location_and_types()


class AccountAnalyticLineInherit(models.Model):
    _inherit = 'account.analytic.line'

    co_location_id = fields.Many2one("account.analytic.account",
                                     string="Co location",
                                     domain=[('analytic_account_type', '=',
                                              'co_location')], required=False,
                                     inverse='_set_co_location', store=True,
                                     readonly=False)

    def _set_co_location(self):
        _logger.info("Co location")


class PurchaseOrderLineCoLocation(models.Model):
    _inherit = 'purchase.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.co_location_id = rec.project_site_id.co_location.id
        return super(PurchaseOrderLineCoLocation, self).get_location_and_types()


class SalesOrderLineInheritCoLocation(models.Model):
    _inherit = 'sale.order.line'

    co_location_id = fields.Many2one(comodel_name="account.analytic.account",
                                     string="Co Location", domain=[
            ('analytic_account_type', '=', 'co_location')], required=False, )

    @api.onchange('project_site_id')
    def get_location_and_types(self):
        for rec in self:
            rec.co_location_id = rec.project_site_id.co_location.id
        return super(SalesOrderLineInheritCoLocation,
                     self).get_location_and_types()
