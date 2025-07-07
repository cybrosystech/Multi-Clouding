from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import xlsxwriter
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class TascAssetTrackingWizard(models.TransientModel):
    _name = 'tasc.asset.tracking.wizard'
    _description = 'TASC Asset Tracking Wizard'

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False,
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To", required=True)
    closed_asset = fields.Selection(selection=[
        ('without_closed_assets', 'Without Closed Assets'),
        ('with_closed_assets', 'With Closed Assets')], string="Closed Asset", default="without_closed_assets")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate date range"""
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_("Date From cannot be later than Date To"))

    def _get_asset_data(self):
        """Fetch asset data based on wizard criteria"""
        try:
            domain = [
                ('company_id', '=', self.company_id.id),
            ]

            if self.date_from:
                domain.append(('acquisition_date', '>=', self.date_from))

            if self.date_to:
                domain.append(('acquisition_date', '<=', self.date_to))

            if self.closed_asset == 'without_closed_assets':
                domain.append(('state', '!=', 'close'))

            _logger.info(f"Searching assets with domain: {domain}")

            assets = self.env['account.asset'].search(domain, order='acquisition_date desc')

            _logger.info(f"Found {len(assets)} assets")
            return assets

        except Exception as e:
            _logger.error(f"Error fetching asset data: {str(e)}")
            raise ValidationError(_("Error fetching asset data: %s") % str(e))

    def _get_asset_field_value(self, asset, field_names):
        """Get field value from asset, trying multiple field names"""
        for field_name in field_names:
            if hasattr(asset, field_name):
                value = getattr(asset, field_name)
                if value:
                    if hasattr(value, 'name'):
                        return value.name
                    return str(value)
        return ''

    def _create_excel_report(self, assets):
        """Create Excel report with asset data"""
        try:
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Asset Tracking Report')

            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })

            header_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'bg_color': '#D7E4BD',
                'border': 1,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center'
            })

            cell_format = workbook.add_format({
                'border': 1,
                'text_wrap': True,
                'valign': 'vcenter',
                'font_size': 10
            })

            date_format = workbook.add_format({
                'border': 1,
                'num_format': 'yyyy-mm-dd',
                'valign': 'vcenter',
                'font_size': 10
            })

            info_format = workbook.add_format({
                'bold': True,
                'font_size': 10,
                'bg_color': '#F2F2F2',
                'border': 1
            })

            summary_format = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'bg_color': '#E6E6FA',
                'border': 1,
                'align': 'center'
            })

            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 18)
            worksheet.set_column('C:C', 18)
            worksheet.set_column('D:D', 18)
            worksheet.set_column('E:E', 14)
            worksheet.set_column('F:F', 10)
            worksheet.set_column('G:G', 14)
            worksheet.set_column('H:H', 18)
            worksheet.set_column('I:I', 18)
            worksheet.set_column('J:J', 18)
            worksheet.set_column('K:K', 15)
            worksheet.set_column('L:L', 15)
            worksheet.set_column('M:M', 15)
            worksheet.set_column('N:N', 17)
            worksheet.set_column('O:O', 10)

            worksheet.merge_range('A1:O1', 'TASC ASSET TRACKING REPORT', title_format)
            worksheet.set_row(0, 25)

            info_row = 2

            headers = ['Asset Name', 'Asset Model', 'Acquisition Date', 'CAPEX Type', 'Barcode', 'SN',
                       'Cost Center', 'Project Site', 'Employee', 'Department', 'Sequence Number', 'Serial Number',
                       'Additional Info', 'Additional Info2', 'Status']

            header_row = info_row

            for col, header in enumerate(headers):
                worksheet.write(header_row, col, header, header_format)

            worksheet.set_row(header_row, 20)

            data_start_row = header_row + 1
            current_row = data_start_row

            for asset in assets:
                asset_name = asset.name or 'Unnamed Asset'
                worksheet.write(current_row, 0, asset_name, cell_format)

                model_name = self._get_asset_field_value(asset, ['model_id'])
                worksheet.write(current_row, 1, model_name, cell_format)

                acquisition_date = asset.acquisition_date if asset.acquisition_date else ''
                worksheet.write(current_row, 2, acquisition_date, date_format)

                capex_type = asset.capex_type if asset.capex_type else ''
                worksheet.write(current_row, 3, capex_type, cell_format)

                barcode = asset.barcode if asset.barcode else ''
                worksheet.write(current_row, 4, barcode, cell_format)

                sn = asset.sn if asset.sn else ''
                worksheet.write(current_row, 5, sn, cell_format)

                cost_center = self._get_asset_field_value(asset, ['analytic_account_id'])
                worksheet.write(current_row, 6, cost_center, cell_format)

                project_site = self._get_asset_field_value(asset, ['project_site_id'])
                worksheet.write(current_row, 7, project_site, cell_format)

                employee = self._get_asset_field_value(asset, ['employee_id'])
                worksheet.write(current_row, 8, employee, cell_format)

                department = self._get_asset_field_value(asset, ['department_id'])
                worksheet.write(current_row, 9, department, cell_format)

                sequence_number =  asset.sequence_number if asset.sequence_number else ''
                worksheet.write(current_row, 10, sequence_number, cell_format)

                serial_number = asset.serial_no if asset.serial_no else ''
                worksheet.write(current_row, 11, serial_number, cell_format)

                additional_info = asset.additional_info if asset.additional_info else ''
                worksheet.write(current_row, 12, additional_info, cell_format)

                additional_info2 = asset.additional_info2 if asset.additional_info2 else ''
                worksheet.write(current_row, 13, additional_info2, cell_format)

                status = asset.state
                worksheet.write(current_row, 14, status, cell_format)

                current_row += 1

            if assets:
                summary_row = current_row + 2
                worksheet.merge_range(f'A{summary_row}:O{summary_row}',
                                      f'SUMMARY: Total {len(assets)} Asset(s) Found', summary_format)
                worksheet.set_row(summary_row - 1, 15)
                worksheet.set_row(summary_row, 25)
            else:
                no_data_row = data_start_row + 2
                worksheet.merge_range(f'A{no_data_row}:O{no_data_row}',
                                      'No assets found matching the selected criteria', summary_format)

            worksheet.freeze_panes(data_start_row, 0)

            if assets:
                worksheet.autofilter(header_row, 0, current_row - 1, 3)

            workbook.close()
            output.seek(0)
            return output.read()

        except Exception as e:
            _logger.error(f"Error creating Excel report: {str(e)}")
            raise ValidationError(_("Error creating Excel report: %s") % str(e))

    def print_asset_tracking_xlsx(self):
        """Generate and download XLSX report"""
        try:
            if not self.company_id:
                raise ValidationError(_("Please select a company"))

            assets = self._get_asset_data()

            excel_data = self._create_excel_report(assets)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company_name = self.company_id.name.replace(' ', '_').replace('/', '_')
            filename = f'TASC_Asset_Report_{company_name}_{timestamp}.xlsx'

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(excel_data),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'description': f'TASC Asset Tracking Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            })

            _logger.info(f"Asset tracking report generated successfully: {filename}")

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f"Unexpected error in print_asset_tracking_xlsx: {str(e)}")
            raise ValidationError(
                _("An unexpected error occurred while generating the report. Please try again or contact your administrator."))