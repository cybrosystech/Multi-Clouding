# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AssetBarcode(models.TransientModel):
    _name = 'asset.barcode'

    barcode = fields.Char(string="Asset barcode")
    quantity_scanned = fields.Integer(string="Scanned Quantity",compute='_compute_scanned_quantity',store=True)
    total_quantity = fields.Integer(string="FAR Quantity",compute='_compute_total_quantity')
    difference = fields.Integer(string="Difference",compute='_compute_difference')
    asset_barcode_line_ids = fields.One2many('asset.barcode.line', 'asset_barcode_id')
    sn_not_in_far = fields.Integer(string="SN not in FAR", compute="_compute_sn_not_in_far")
    sn_in_far_pending = fields.Integer(string="SN in FAR Pending", compute="_compute_sn_in_far_pending")
    is_validated = fields.Boolean(string="Complete")
    active = fields.Boolean(default=True)

    @api.depends('total_quantity', 'quantity_scanned')
    def _compute_sn_not_in_far(self):
        for record in self:
            scanned_sns = set(record.asset_barcode_line_ids.mapped('serial_number'))

            far_assets = self.env['account.asset'].search([('barcode', '=', record.barcode)])
            far_sns = set(far_assets.mapped('sn'))
            not_in_far = scanned_sns - far_sns
            record.sn_not_in_far = len(not_in_far)

    @api.depends('quantity_scanned','total_quantity')
    def _compute_sn_in_far_pending(self):
        for rec in self:
            rec.sn_in_far_pending = rec.total_quantity - rec.quantity_scanned

    @api.depends('asset_barcode_line_ids')
    def _compute_scanned_quantity(self):
        for rec in self:
            if rec.asset_barcode_line_ids:
                rec.quantity_scanned = len(rec.asset_barcode_line_ids.ids)
            else:
                rec.quantity_scanned = 0

    @api.depends('barcode')
    def _compute_total_quantity(self):
        for rec in self:
            if rec.barcode:
                rec.total_quantity = self.env['account.asset'].search_count([('barcode','=',rec.barcode)])
            else:
                rec.total_quantity = 0

    @api.depends('quantity_scanned','total_quantity')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.total_quantity-rec.quantity_scanned

    @api.model
    def barcode_search(self, last_code, asset_barcode_id):
        """Asset barcode line is created and product is added by checking
        the barcode. Args contain the barcode of product and asset barcode ID."""
        last_code = last_code.split("/")
        if last_code:
            barcode = last_code[0] if last_code[0] else False
            sn = last_code[1] if len(last_code) > 1 and last_code[1] else False

            if barcode and sn:
                linked_asset = self.env['account.asset'].search([
                    ('barcode', '=', barcode),
                    ('sn', '=', sn)
                ], limit=1)

                asset = self.env['account.asset'].search([
                    ('barcode', '=', barcode),
                    ('sn', '=', sn)
                ])

                asset_barcode = self.env['asset.barcode'].search([
                    ('barcode', '=', barcode)
                ], limit=1)

                if not asset_barcode:
                    asset_barcode = self.env['asset.barcode'].create({
                        'barcode': barcode,
                    })

                if not asset:
                    existing_line = self.env['asset.barcode.line'].search([
                        ('asset_barcode_id', '=', asset_barcode.id),
                        ('serial_number', '=', sn),
                        ('barcode', '=', barcode),
                    ], limit=1)

                    if not existing_line:
                        asset_barcode.asset_barcode_line_ids.create({
                            'asset_barcode_id': asset_barcode.id,
                            'barcode': barcode,
                            'serial_number': sn,
                            'asset_id': linked_asset.id if linked_asset else False,
                        })
                else:
                    for ass in asset:
                        existing_line = self.env['asset.barcode.line'].search([
                            ('asset_barcode_id', '=', asset_barcode.id),
                            ('asset_id', '=', ass.id)
                        ], limit=1)

                        if not existing_line:
                            asset_barcode.asset_barcode_line_ids.create({
                                'asset_barcode_id': asset_barcode.id,
                                'asset_id': ass.id,
                            })

            else:
                barcode = last_code[0] if last_code[0] else False
                asset = self.env['account.asset'].search([
                    ('barcode', '=', barcode)
                ])
                asset_barcode = self.env['asset.barcode'].search([
                    ('barcode', '=', barcode)
                ], limit=1)

                if not asset_barcode:
                    asset_barcode = self.env['asset.barcode'].create({
                        'barcode': barcode,
                    })

                for ass in asset:
                    existing_line = self.env['asset.barcode.line'].search([
                        ('asset_barcode_id', '=', asset_barcode.id),
                        ('asset_id', '=', ass.id)
                    ], limit=1)

                    if not existing_line:
                        asset_barcode.asset_barcode_line_ids.create({
                            'asset_barcode_id': asset_barcode.id,
                            'asset_id': ass.id,
                        })

        return

    def action_open_scanner(self):
        return {
            "type": "ir.actions.client",
            "tag": "tasManualBarcodeScanner",
            "target": "new",
            "name": "Open Scanner",
        }

    def action_view(self):
        self.ensure_one()
        scanned_sns = self.asset_barcode_line_ids.mapped('serial_number')
        all_assets = self.env['account.asset'].search([('barcode', '=', self.barcode)])
        pending_assets = all_assets.filtered(lambda a: a.sn not in scanned_sns)
        asset_ids = pending_assets.ids[:self.sn_in_far_pending]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Assets in FAR Pending',
            'res_model': 'account.asset',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', asset_ids)],
            'target': 'current',
        }

    def write(self, vals):
        res = super().write(vals)
        if 'is_validated' in vals:
            for rec in self:
                if vals['is_validated']:
                    if rec.active:
                        rec.active = False
                else:
                    if not rec.active:
                        rec.active = True
        return res

    class AssetBarcodeLine(models.TransientModel):
        _name = 'asset.barcode.line'

        asset_id = fields.Many2one('account.asset', string="Asset")
        asset_model_id = fields.Many2one('account.asset',related='asset_id.model_id')
        seq_number = fields.Char(related='asset_id.sequence_number',readonly=False,store=True)
        serial_number = fields.Char(related='asset_id.sn',readonly=False,store=True)
        barcode = fields.Char(related='asset_id.barcode',readonly=False,store=True)
        asset_barcode_id = fields.Many2one('asset.barcode', string="Asset Barcode")
