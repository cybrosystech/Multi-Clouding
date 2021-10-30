# -*- coding: utf-8 -*-
# from odoo import http


# class AnalyticAccountTypes(http.Controller):
#     @http.route('/analytic_account_types/analytic_account_types/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_account_types/analytic_account_types/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_account_types.listing', {
#             'root': '/analytic_account_types/analytic_account_types',
#             'objects': http.request.env['analytic_account_types.analytic_account_types'].search([]),
#         })

#     @http.route('/analytic_account_types/analytic_account_types/objects/<model("analytic_account_types.analytic_account_types"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_account_types.object', {
#             'object': obj
#         })
