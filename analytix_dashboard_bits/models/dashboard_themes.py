from odoo import fields, models, api, _
import re

class DashboardThemes(models.Model):
    _name = 'dashboard.themes'
    _description = 'Dashboard Themes'

    name = fields.Char(required=True)
    is_default = fields.Boolean(string='Use this theme as default theme')

    color_1 = fields.Char("Color 1")
    color_2 = fields.Char("Color 2")
    color_3 = fields.Char("Color 3")
    color_4 = fields.Char("Color 4")
    color_5 = fields.Char("Color 5")
    color_6 = fields.Char("Color 6")
    color_7 = fields.Char("Color 7")
    color_8 = fields.Char("Color 8")

    logo = fields.Image()

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if res.is_default:
            recs = self.search([('id', '!=', res.id)])
            for rec in recs:
                rec.write({'is_default': False}) 
                
        online_partner = self.env['res.users'].sudo().search([]).filtered(
            lambda x: x.im_status in ['leave_online', 'online']).mapped("partner_id").ids
        updates = {'dashboard_ids': []}
        notification = [[(self._cr.dbname, 'res.partner', partner_id), 'theme_add_nitify',
                         {'type': 'NotifyUpdates', 'updates': updates}] for partner_id in online_partner]
        self.env['bus.bus']._sendmany(notification) 
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default', False):
            recs = self.search([('id', '!=', self.id)])
            for rec in recs:
                rec.write({'is_default': False})
        return res

    @api.onchange('logo')
    def _onchange_logo(self):
        if self.logo:
            color1, color2 = self.env['base.document.layout'].extract_image_primary_secondary_colors(self.logo)
            if color1 and color2:
                res = self.set_recommended_palette(color1, color2)
                if res:
                    self.write({
                        "color_1": res['color1'],
                        "color_2": res['color2'],
                        "color_3": res['color3'],
                        "color_4": res['color4'],
                        "color_5": res['color5'],
                        "color_6": res['color6'],
                        "color_7": res['color7'],
                        "color_8": res['color8'],
                    })

    @api.model
    def get_themes(self):
        res = {}
        for rec in self.search([]):
            res.update({rec.id: rec.name})
        return res

    @api.model
    def get_color_palette(self):
        if self:
            lst = []

            if self.color_1:
                lst.append(self.color_1)

            if self.color_2:
                lst.append(self.color_2)

            if self.color_3:
                lst.append(self.color_3)

            if self.color_4:
                lst.append(self.color_4)

            if self.color_5:
                lst.append(self.color_5)

            if self.color_6:
                lst.append(self.color_6)

            if self.color_7:
                lst.append(self.color_7)

            if self.color_8:
                lst.append(self.color_8)

            return lst

        else:

            return ['#35979C', '#F6F6F6', '#685563', '#383E45', '#5B4877', '#35519A', '#0FE7C0', '#9CACD3']

    def convert_css_color_to_rgba(self, css_color):
        rgba = re.match(r'^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$', css_color)
        if rgba:
            if rgba.group(4) is None:
                opacity = 1
            else:
                opacity = float(rgba.group(4))
            return {
                'red': int(rgba.group(1)),
                'green': int(rgba.group(2)),
                'blue': int(rgba.group(3)),
                'opacity': round(opacity * 100)
            }

        if re.match(r'^#[0-9A-Fa-f]{6}$', css_color) or re.match(r'^#[0-9A-Fa-f]{8}$', css_color):
            hex_color = css_color.lstrip("#")
            red = int(hex_color[0:2], 16)
            green = int(hex_color[2:4], 16)
            blue = int(hex_color[4:6], 16)
            if len(hex_color) == 8:
                opacity = int(hex_color[6:8], 16) / 255
            else:
                opacity = 1.0
            return {
                'red': red,
                'green': green,
                'blue': blue,
                'opacity': int(opacity * 100)
            }

        return False

    def convert_rgba_to_css_color(self, r, g, b, a=None):
        if (
            not isinstance(r, int) or not 0 <= r <= 255
            or not isinstance(g, int) or not 0 <= g <= 255
            or not isinstance(b, int) or not 0 <= b <= 255
        ):
            return False

        if a is None or abs(a - 100) < 1e-9:
            rr = f"{r:02X}"
            gg = f"{g:02X}"
            bb = f"{b:02X}"
            return f"#{rr}{gg}{bb}".upper()
        return f"rgba({r}, {g}, {b}, {round(a / 100, 3)})"

    def mix_css_colors(self, css_color1, css_color2, weight):
        rgba1 = self.convert_css_color_to_rgba(css_color1)
        rgba2 = self.convert_css_color_to_rgba(css_color2)
        rgb1 = [rgba1['red'], rgba1['green'], rgba1['blue']]
        rgb2 = [rgba2['red'], rgba2['green'], rgba2['blue']]
        
        r = round(rgb2[0] + (rgb1[0] - rgb2[0]) * weight)
        g = round(rgb2[1] + (rgb1[1] - rgb2[1]) * weight)
        b = round(rgb2[2] + (rgb1[2] - rgb2[2]) * weight)

        return self.convert_rgba_to_css_color(r, g, b, rgba1['opacity'])

    def set_recommended_palette(self, color1, color2):
        if color1 and color2:
            if color1 == color2:
                color2 = self.mix_css_colors("#FFFFFF", color1, 0.2)
            recommended_palette = {
                "color1": color1,
                "color2": color2,
                "color3": self.mix_css_colors("#FFFFFF", color2, 0.9),
                "color4": self.mix_css_colors("#FFFFFF", color1, 0.1),
                "color5": "#FFFFFF",
                "color6": self.mix_css_colors(color1, "#000000", 0.75),
                "color7": self.mix_css_colors(color2, "#000000", 0.5),
                "color8": self.mix_css_colors(color1, color2, 0.5),
            }

            return recommended_palette
        return False