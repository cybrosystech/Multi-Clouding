from datetime import timedelta
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    department_id = fields.Many2one('hr.department', string="Department",
                                    related='employee_id.department_id', readonly=True, tracking=True)

    def _prepare_report_data(self):
        data = []
        for rec in self:
            data.append({
                'barcode': rec.barcode,
                'serial_no':rec.sn,
            })
        xml_id = 'tasc_asset_tracking.report_product_template_label_asset'

        return xml_id, data

    def action_print_label(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action

    def action_bulk_print_label(self):
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action