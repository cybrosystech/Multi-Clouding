# -*- coding: utf-8 -*-
# author     :guoyihot@outlook.com
# date       ：
# description:

from odoo import models, fields, api,_
from odoo.exceptions import UserError

class BaseImport(models.TransientModel):
    _inherit="base_import.import"
    
    '''v11
    @api.multi
    def do(self, fields, options, dryrun=False):   
        #import rpdb2;rpdb2.start_embedded_debugger('111',fAllowRemote=True)       
        return super(BaseImport,self.with_context(dryrun=dryrun,import_order_line=options.get('import_order_line'))).do(fields,options,dryrun)
    '''
    def do(self, fields, columns, options, dryrun=False):
        '''
        v12
        '''
        return super(BaseImport,self.with_context(dryrun=dryrun,import_order_line=options.get('import_order_line'))).do(fields,columns,options,dryrun)

    @api.model
    def _convert_import_data(self, fields, options):
        data,fields=super(BaseImport,self)._convert_import_data(fields,options)
        if self._context.get('import_order_line'):
            import_field=options.get('import_field')
            order_id=options.get('order_id')
            if import_field and order_id:
                fields.append(import_field)
                for row in data:
                    row.append(order_id)
           
        return data,fields



class PurchaseOrderLine(models.Model):
    _inherit="purchase.order.line"

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name','date_planned', 'price_unit', 'product_uom']
        if values.get('order_id') and values.get('product_id') and any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.onchange_product_id()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        return res
    
    @api.model    
    def create(self, vals):
        if self._context.get('import_order_line'):
            vals.update(self._prepare_add_missing_fields(vals))
            return super(PurchaseOrderLine,self).create(vals)
        return super(PurchaseOrderLine,self).create(vals)


        