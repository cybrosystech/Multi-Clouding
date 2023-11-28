from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
from io import StringIO, BytesIO
import pandas
import requests

class IZITools(models.TransientModel):
    _inherit = 'izi.tools'

    @api.model
    def lib(self, key):
        lib = {
            'pandas': pandas,
            'requests': requests,
        }
        if key in lib:
            return lib[key]
        return super(IZITools, self).lib(key)
    
    @api.model
    def requests(self, method, url, headers={}, data={}):
        response = requests.request(method, url=url, headers=headers, data=data)
        return response

    @api.model
    def requests_io(self, method, url, headers={}, data={}):
        response = requests.request(method, url=url, headers=headers, data=data)
        return io.StringIO(response.content.decode('utf-8'))
    
    @api.model
    def read_csv(self, url, **kwargs):
        data = []
        try:
            df = pandas.read_csv(
                url,
                **kwargs
            )
            data = df.to_dict('records')
        except Exception as e:
            raise UserError(str(e))
        return data
    
    @api.model
    def read_excel(self, url, **kwargs):
        data = []
        try:
            df = pandas.read_excel(
                url,
                **kwargs
            )
            data = df.to_dict('records')
        except Exception as e:
            raise UserError(str(e))
        return data

    @api.model
    def read_attachment(self, attachment, **kwargs):
        data = []
        if not attachment:
            raise UserError('Attachment Not Found')
        try:
            if attachment.mimetype in ('application/vnd.ms-excel', 'text/csv'):
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
            elif attachment.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                df = pandas.read_excel(BytesIO(attachment.raw))
            else:
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
            data = df.to_dict('records')
        except Exception as e:
            raise UserError(str(e))
        return data

    @api.model
    def read_attachment_by_name(self, attachment_name, **kwargs):
        Attachment = self.env['ir.attachment']
        attachment = Attachment.search([('name', '=', attachment_name)], limit=1)
        data = []
        if not attachment_name:
            raise UserError('Attachment Name Not Found')
        try:
            if attachment.mimetype in ('application/vnd.ms-excel', 'text/csv'):
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
            elif attachment.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                df = pandas.read_excel(BytesIO(attachment.raw))
            else:
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
            data = df.to_dict('records')
        except Exception as e:
            raise UserError(str(e))
        return data
    
    @api.model
    def read_attachment_df(self, attachment, **kwargs):
        df = False
        if not attachment:
            raise UserError('Attachment Not Found')
        try:
            if attachment.mimetype in ('application/vnd.ms-excel', 'text/csv'):
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
            elif attachment.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                df = pandas.read_excel(BytesIO(attachment.raw))
            else:
                df = pandas.read_csv(BytesIO(attachment.raw), encoding="latin1")
        except Exception as e:
            raise UserError(str(e))
        return df

    @api.model
    def read_google_spreadsheet(self, gsheetid, gsheetname=''):
        try:
            gsheet_url = "https://docs.google.com/spreadsheets/d/{}/gviz/tq?tqx=out:csv&sheet={}".format(
                gsheetid, gsheetname)
            df = pandas.read_csv(gsheet_url)
            data = df.to_dict('records')
        except Exception as e:
            raise UserError(str('Something wrong from your google spreadsheet.\n\nError Details:\n%s' % e))
        return data
    
