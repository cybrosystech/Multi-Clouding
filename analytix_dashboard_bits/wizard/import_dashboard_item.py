from odoo import api, models, fields, _
import json
import base64
from odoo.tools.safe_eval import safe_eval
from odoo.addons.advanced_web_domain_widget.models.domain_prepare import prepare_domain_v2

class ImportDashboardItem(models.TransientModel):
    _name = "import.dashboard.item"
    _description = "Import Dashboard Item"

    name = fields.Char("Name")
    import_dashboard_item_doc = fields.Binary("Import Dashboard Item Document")

    def import_dashboard_item_action(self):
        # try:
        if self.import_dashboard_item_doc:
            import_doc = base64.b64decode(self.import_dashboard_item_doc).decode('utf-8')
            json_data = json.loads(import_doc)

            dashboard_item_bits_obj = self.env['dashboard.item.bits']
            for record in json_data.keys():
                model_dic=json_data[record].get('model')
                model = self.env['ir.model'].search([('model', '=', model_dic.get('model'))])
                field_id = self.env['ir.model.fields'].sudo().search(
                                        [('model_id.name', '=', model_dic.get('name')), ('name', '=', json_data[record].get('statistics_field'))])
                dashboard = self._context['dashboard_id']
                record_name = json_data[record].get('name') if json_data[record].get('name') else '' + '[import]'

                action = self.env['ir.actions.act_window'].sudo().search([('name', '=', json_data[record].get('action_id'))])

                list_view_field=[]
                for field in json_data[record].get('list_view_field_ids'):
                    list_view_field_id=self.env['ir.model.fields'].search([('model_id.name','=',model_dic.get('name')),('name', '=', field)])
                    if list_view_field_id.id:
                            list_view_field.append(list_view_field_id.id)
                chart_measure_field=[]
                for field in json_data[record].get('chart_measure_field_ids'):
                    chart_measure_field_id=self.env['ir.model.fields'].search([('model_id.name','=',model_dic.get('name')),('name', '=', field)])
                    chart_measure_field.append(chart_measure_field_id.id)

                bar_line_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('bar_line_field_id')),('model_id.name','=',model_dic.get('name'))])
                chart_groupby_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('chart_groupby_field')),('model_id.name','=',model_dic.get('name'))])
                chart_sub_groupby_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('chart_sub_groupby_field')),('model_id.name','=',model_dic.get('name'))])
                chart_sort_by_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('chart_sort_by_field')),('model_id.name','=',model_dic.get('name'))])
                b_trend_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('b_trend_field_id')),('model_id.name','=',model_dic.get('name'))])
                b_measure_field = self.env['ir.model.fields'].search([('name', '=', json_data[record].get('b_measure_field_id')),('model_id.name','=',model_dic.get('name'))])

                company = self.env['res.company'].search([('name', '=', json_data[record].get('company_id'))])
                color_theme = self.env['dashboard.themes'].search([('name', '=', json_data[record].get('color_theme'))])
                dashboard_grid_config = self.env['dashboard.gird.config'].search([('id', '=', json_data[record].get('dashboard_grid_config_id'))])

                data = {
                        'name': record_name,
                        'model_id' : model.id,
                        "item_title": json_data[record].get('item_title'),
                        "statistics_item_title": json_data[record].get('statistics_item_title'),
                        "view_data": json_data[record].get('view_data'),
                        "trend_display_style": json_data[record].get('trend_display_style'),
                        "trend_primary_color": json_data[record].get('trend_primary_color'),
                        "apply_background": json_data[record].get('apply_background'),
                        "action_id": action.mapped("id")[0] if action else False,
                        "kpi_display_style": json_data[record].get('kpi_display_style'),
                        "kpi_primary_color": json_data[record].get('kpi_primary_color'),
                        "is_smooth_line": json_data[record].get('is_smooth_line'),
                        "is_area_style": json_data[record].get('is_area_style'),
                        "is_background": json_data[record].get('is_background'),
                        "horizontal_chart": json_data[record].get('horizontal_chart'),
                        "bar_stack": json_data[record].get('bar_stack'),
                        "is_polar": json_data[record].get('is_polar'),
                        "circular_chart": json_data[record].get('circular_chart'),
                        "doughnut_chart": json_data[record].get('doughnut_chart'),
                        "half_pie": json_data[record].get('half_pie'),
                        "list_view_style": json_data[record].get('list_view_style'),
                        "list_view_field_ids": list_view_field if len(list_view_field) > 0 and list_view_field[0] else False,
                        "show_record_edit_button": json_data[record].get('show_record_edit_button'),
                        "records_per_page": json_data[record].get('records_per_page'),
                        "chart_measure_field_ids": chart_measure_field if len(chart_measure_field) > 0 and chart_measure_field[0] else False,
                        "bar_line_field_id": bar_line_field.id,
                        "is_bar_line": json_data[record].get('is_bar_line'),
                        "display_order": json_data[record].get('display_order'),
                        "chart_groupby_field": chart_groupby_field.id,
                        "chart_sub_groupby_field":chart_sub_groupby_field.id,
                        "chart_sort_by_field": chart_sort_by_field.id,
                        "chart_sort_by_order": json_data[record].get('chart_sort_by_order'),
                        "record_limit": json_data[record].get('record_limit'),
                        "dashboard_grid_config_id": dashboard_grid_config.mapped("id")[0] if dashboard_grid_config else False,
                        "chart_preview_bits": json_data[record].get('chart_preview_bits'),
                        'b_trend_field_id':  b_trend_field.id,
                        "b_measure_type": json_data[record].get("b_measure_type"),
                        "b_measure_field_id": b_measure_field.id,
                        "b_show_val": json_data[record].get('b_show_val'),
                        "company_id": company.id,
                        "kpi_target": json_data[record].get('kpi_target'),
                        "model_name": json_data[record].get('model_name'),
                        "color_theme": color_theme.id,
                        "query": json_data[record].get('query'),
                        "stats_value_by_qry":json_data[record].get('stats_value_by_qry'),
                        "x_axis": json_data[record].get('x_axis'),
                        "bar_line_measure":json_data[record].get('bar_line_measure'),
                        "y_axis": json_data[record].get('y_axis'),
                        'bits_dashboard_id' : dashboard,
                        "is_limit_record":True if json_data[record].get('is_limit_record') else False,
                        'item_type':json_data[record].get('item_type'),
                        'is_query':json_data[record].get('is_query'),
                        "v_records_per_page":json_data[record].get('v_records_per_page'),
                        'onclick_action':json_data[record].get('onclick_action'),
                        'statistics_with_trend':json_data[record].get('statistics_with_trend'),
                        'display_data_type':json_data[record].get('display_data_type'),
                        'statistics_field':field_id.id,
                        'show_currency':json_data[record].get('show_currency'),
                        'media_option':json_data[record].get('media_option'),
                        'icon_bits':json_data[record].get('icon_bits'),
                        'display_style':json_data[record].get('display_style'),
                        'background_color':json_data[record].get('background_color'),
                        'font_color':json_data[record].get('font_color'),
                        'icon_color':json_data[record].get('icon_color'),
                        'is_border':json_data[record].get('is_border'),
                        'border_position':json_data[record].get('border_position'),
                        'border_color':json_data[record].get('border_color'),
                        "legend_position": json_data[record].get('legend_position'),
                        "show_legend": json_data[record].get('show_legend'),
                        "lable_position": json_data[record].get('lable_position'),
                        "show_lable": json_data[record].get('show_lable'),
                        "lable_format": json_data[record].get('lable_format'),
                        "stats_chart_y_by_qry": json_data[record].get('stats_chart_y_by_qry'),
                        "stats_chart_x_by_qry": json_data[record].get('stats_chart_x_by_qry'),
                        "icon_background": json_data[record].get('icon_background'),
                        "embade_code":json_data[record].get('embade_code'),
                    }
                try:
                    if model.model and json_data[record].get('item_domain'):
                        new_domain = []
                        for domm in safe_eval(json_data[record].get('item_domain')):
                            if "date_filter" in domm:
                                date_domain = prepare_domain_v2(domm)
                                for dom in date_domain:
                                    new_domain.append(dom)
                            else:
                                new_domain.append(domm)
                        self.env[model.model].search(new_domain)
                        data['item_domain'] = json_data[record].get('item_domain')
                except:
                    pass
                import_record = dashboard_item_bits_obj.create(data)
            

       
        
   
