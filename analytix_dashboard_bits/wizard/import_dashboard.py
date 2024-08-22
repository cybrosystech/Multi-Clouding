from odoo import api, models, fields, _
import json
import base64
from odoo.tools.safe_eval import safe_eval
from odoo.addons.advanced_web_domain_widget.models.domain_prepare import prepare_domain_v2

class ImportDashboard(models.TransientModel):
    _name = "import.dashboard"
    _description = "Import Dashboard"

    name = fields.Char("Name")
    import_doc = fields.Binary("Import Document")

    def import_dashboard_action(self):
        # try:
        if self.import_doc:
            import_doc = base64.b64decode(self.import_doc).decode('utf-8')
            json_data = json.loads(import_doc)

            dashboard_bits_obj = self.env['dashboard.bits']
            filter_obj = self.env['dashboard.filter.bits']
            dashboard_item_obj = self.env['dashboard.item.bits']
            for record in json_data.keys():
                # pass
                menu=json_data[record]['parent_menu']
                menu_id = self.env['ir.ui.menu'].sudo().search(
                                [('name', '=', menu['name']), ('parent_id.name', '=', menu['parent_id'])])
                # for dashboard in self:
                record_dashboard_name = json_data[record].get('name') + '[import]'
                theme = self.env['dashboard.themes'].search([('name', '=', json_data[record].get('default_color_theme'))])
                company = self.env['res.company'].search([('name', '=', json_data[record].get('company_id'))])
                data = {
                        'name': record_dashboard_name,
                        "is_main_menu": json_data[record].get('is_main_menu'),
                        "d_icon_bits": json_data[record].get('d_icon_bits'),
                        "menu_sequence": json_data[record].get('menu_sequence'),
                        'menu_name' : json_data[record].get('menu_name'),
                        'parent_menu_id': menu_id.id,
                        "grid_config": json_data[record].get('grid_config'),
                        "time_frame": json_data[record].get('time_frame'),
                        "company_id": company.id,
                        "start_date": json_data[record].get('start_date'),
                        "end_date": json_data[record].get('end_date'),
                        'default_time_frame':json_data[record].get('default_time_frame'),
                        # 'default_color_theme':theme,
                        'default_view_mode':json_data[record].get('default_view_mode'),
                        'active':json_data[record].get('active'),
                        'is_public': json_data[record].get('active', False),
                    }
                if theme.id:
                    data['default_color_theme'] = theme.id
                
                import_record = dashboard_bits_obj.create(data)


                grid_config = json.loads(json_data[record].get('grid_config'))
                new_grid_config = {}
                
                if json_data[record].get('start_date'):
                    import_record['start_date'] = json_data[record].get('start_date')

                if json_data[record].get('end_date'):
                    import_record['end_date'] = json_data[record].get('end_date')

                for filter in json_data[record].get('filter_ids'):
                    model = self.env['ir.model'].search([('model', '=', filter['model']['model'])])
                    field_id = self.env['ir.model.fields'].search(
                                        [('model_id.name', '=', filter['model']['name']), ('name', '=', filter.get('field_id'))])
                    
                    if model and field_id:
                        filter_obj.create({

                            'dashboard_id':import_record.id,
                            'name': filter.get('name'),
                            'model_id': model.id,
                            'field_id': field_id.id,
                            'active': True,
                        })

                for dashbord_id in json_data[record].get('dashboard_item_ids'):

                    model_dic=dashbord_id.get('model')
                    model = self.env['ir.model'].search([('model', '=', model_dic.get('model'))])
                    field_id = self.env['ir.model.fields'].sudo().search(
                                            [('model_id.name', '=', model_dic.get('name')), ('name', '=', dashbord_id.get('statistics_field'))])
                    dashboard = self.env['dashboard.bits'].search([('name', '=', dashbord_id.get('dashboard'))])
                    record_item_name = dashbord_id.get('name', '') if dashbord_id.get('name', '') else '' + '[import]'
                    action = self.env['ir.actions.act_window'].search([('name', '=', dashbord_id.get('action_id'))])

                    list_view_field=[]
                    for field in dashbord_id.get('list_view_field_ids'):
                        list_view_field_id=self.env['ir.model.fields'].search([('model_id.name','=',model_dic.get('name')),('name', '=', field)])
                        if list_view_field_id.id:
                            list_view_field.append(list_view_field_id.id)
                        
                    # list_view_field = self.env['ir.model.fields'].search([('name', 'in', dashbord_id.get('list_view_field_ids'))])
                    chart_measure_field=[]
                    for field in dashbord_id.get('chart_measure_field_ids'):
                        chart_measure_field_id=self.env['ir.model.fields'].search([('model_id.name','=',model_dic.get('name')),('name', '=', field)])
                        chart_measure_field.append(chart_measure_field_id.id) 

                    bar_line_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('bar_line_field_id')),('model_id.name','=',model_dic.get('name'))])
                    chart_groupby_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('chart_groupby_field')),('model_id.name','=',model_dic.get('name'))])
                    chart_sub_groupby_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('chart_sub_groupby_field')),('model_id.name','=',model_dic.get('name'))])
                    chart_sort_by_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('chart_sort_by_field')),('model_id.name','=',model_dic.get('name'))])
                    b_trend_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('b_trend_field_id')),('model_id.name','=',model_dic.get('name'))])
                    b_measure_field = self.env['ir.model.fields'].search([('name', '=', dashbord_id.get('b_measure_field_id')),('model_id.name','=',model_dic.get('name'))])

                    company = self.env['res.company'].search([('name', '=', dashbord_id.get('company_id'))])
                    color_theme = self.env['dashboard.themes'].search([('name', '=', dashbord_id.get('color_theme'))])
                    dashboard_grid_config = self.env['dashboard.gird.config'].search([('id', '=', dashbord_id.get('dashboard_grid_config_id'))])

                    
                    if dashbord_id.get('is_query') and dashbord_id.get('query'):
                        try:
                            query_str = dashbord_id.get('query')
                            new_env = self.pool.cursor()

                            new_env.execute("with c_query as (" + query_str + ")" +
                                            "select * from c_query limit %(limit)s",
                                            {'limit': 5})
                        except:
                            dashbord_id['query'] = ''
                            dashbord_id['stats_value_by_qry'] = ''
                        finally:
                            new_env.close()
                    data = {
                        'name': record_item_name,
                        'model_id' : model.id,
                        "item_title": dashbord_id.get('item_title'),
                        "statistics_item_title": dashbord_id.get('statistics_item_title'),
                        "view_data": dashbord_id.get('view_data'),
                        "trend_display_style": dashbord_id.get('trend_display_style'),
                        "trend_primary_color": dashbord_id.get('trend_primary_color'),
                        "apply_background": dashbord_id.get('apply_background'),
                        "action_id": action.mapped("id")[0] if action else False,
                        "kpi_display_style": dashbord_id.get('kpi_display_style'),
                        "kpi_primary_color": dashbord_id.get('kpi_primary_color'),
                        "is_smooth_line": dashbord_id.get('is_smooth_line'),
                        "is_area_style": dashbord_id.get('is_area_style'),
                        "is_background": dashbord_id.get('is_background'),
                        "is_limit_record":True if dashbord_id.get('is_limit_record') else False,
                        "horizontal_chart": dashbord_id.get('horizontal_chart'),
                        "bar_stack": dashbord_id.get('bar_stack'),
                        "is_polar": dashbord_id.get('is_polar'),
                        "circular_chart": dashbord_id.get('circular_chart'),
                        "doughnut_chart": dashbord_id.get('doughnut_chart'),
                        "half_pie": dashbord_id.get('half_pie'),
                        "list_view_style": dashbord_id.get('list_view_style'),
                        "list_view_field_ids": list_view_field if len(list_view_field) > 0 and list_view_field[0] else False,
                        "show_record_edit_button": dashbord_id.get('show_record_edit_button'),
                        "records_per_page": dashbord_id.get('records_per_page'),
                        "chart_measure_field_ids": chart_measure_field if len(chart_measure_field) > 0 and chart_measure_field[0] else False,
                        "bar_line_field_id": bar_line_field.id,
                        "is_bar_line": dashbord_id.get('is_bar_line'),
                        "display_order": dashbord_id.get('display_order'),
                        "chart_groupby_field": chart_groupby_field.id,
                        "chart_sub_groupby_field":chart_sub_groupby_field.id,
                        "chart_sort_by_field": chart_sort_by_field.id,
                        "chart_sort_by_order": dashbord_id.get('chart_sort_by_order'),
                        "record_limit": dashbord_id.get('record_limit'),
                        "dashboard_grid_config_id": dashboard_grid_config.mapped("id")[0] if dashboard_grid_config else False,
                        "chart_preview_bits": dashbord_id.get('chart_preview_bits'),
                        'b_trend_field_id': b_trend_field.id,
                        "b_measure_type": dashbord_id.get("b_measure_type"),
                        "b_measure_field_id": b_measure_field.id,
                        "b_show_val": dashbord_id.get('b_show_val'),
                        "company_id": company.id,
                        "kpi_target": dashbord_id.get('kpi_target'),
                        "model_name": dashbord_id.get('model_name'),
                        "color_theme": color_theme.id,
                        "query": dashbord_id.get('query'),
                        "x_axis": dashbord_id.get('x_axis'),
                        "y_axis": dashbord_id.get('y_axis'),
                        'bits_dashboard_id' : import_record.id,
                        'item_type':dashbord_id.get('item_type'),
                        'is_query':dashbord_id.get('is_query'),
                        'onclick_action':dashbord_id.get('onclick_action'),
                        'statistics_with_trend':dashbord_id.get('statistics_with_trend'),
                        'display_data_type':dashbord_id.get('display_data_type'),
                        'statistics_field':field_id.id,
                        'show_currency':dashbord_id.get('show_currency'),
                        'media_option':dashbord_id.get('media_option'),
                        'icon_bits':dashbord_id.get('icon_bits'),
                        'display_style':dashbord_id.get('display_style'),
                        'background_color':dashbord_id.get('background_color'),
                        'font_color':dashbord_id.get('font_color'),
                        'icon_color':dashbord_id.get('icon_color'),
                        'is_border':dashbord_id.get('is_border'),
                        'border_position':dashbord_id.get('border_position'),
                        'border_color':dashbord_id.get('border_color'),
                        "legend_position": dashbord_id.get('legend_position'),
                        "show_legend": dashbord_id.get('show_legend'),
                        "lable_position": dashbord_id.get('lable_position'),
                        "show_lable": dashbord_id.get('show_lable'),
                        "lable_format": dashbord_id.get('lable_format'),
                        "stats_chart_y_by_qry": dashbord_id.get('stats_chart_y_by_qry'),
                        "stats_chart_x_by_qry": dashbord_id.get('stats_chart_x_by_qry'),
                        'stats_value_by_qry': dashbord_id.get('stats_value_by_qry'),    
                        'icon_background':dashbord_id.get('icon_background'),
                        'embade_code':dashbord_id.get('embade_code'),
                    }
                    try:
                        if model.model and dashbord_id.get('item_domain'):
                            new_domain = []
                            for domm in safe_eval(dashbord_id.get('item_domain')):
                                if "date_filter" in domm:
                                    date_domain = prepare_domain_v2(domm)
                                    for dom in date_domain:
                                        new_domain.append(dom)
                                else:
                                    new_domain.append(domm)
                            self.env[model.model].search(new_domain)
                            data['item_domain'] = dashbord_id.get('item_domain')
                    except:
                        pass
                    dashboard_item = dashboard_item_obj.create(data)

                    if dashbord_id.get('id') and isinstance(grid_config, dict):
                        new_conf = grid_config.get(str(dashbord_id.get('id')))
                        if new_conf:
                            new_grid_config['item_' + str(dashboard_item.id)] = new_conf if new_conf else False
                
                import_record.write({"grid_config": json.dumps(new_grid_config)})

         
        
   
