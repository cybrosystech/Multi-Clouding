from collections import defaultdict
from odoo import _, models
from odoo.exceptions import UserError


def _prepare_data(env, docids, data):
    asset_ids = env['account.asset'].search([('id','in',data["context"].get('active_ids'))])
    data = []
    for rec in asset_ids:
        data.append({
        'barcode': rec.barcode,
        'serial_no': rec.sn,
    })
    return {"data": data}


class ReportProductTemplateLabelAsset(models.AbstractModel):
    _name = 'report.tasc_asset_tracking.report_label_asset'
    _description = 'Product Label Report on Asset'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)
