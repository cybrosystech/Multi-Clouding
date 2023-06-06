from odoo import models, fields


class AccountMoveLeaseSecurity(models.Model):
    _inherit = 'account.move'

    lease_security_advance_id = fields.Many2one('leasee.security.advance')


class AccountMoveLineConstraints(models.Model):
    _inherit = "account.move.line"

    def init(self):
        super().init()
        self.env.cr.execute('''
        SELECT
        CONSTRAINT_NAME, CONSTRAINT_TYPE
        FROM
        INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
        TABLE_NAME = 'account_move_line' and CONSTRAINT_NAME = 'account_move_line_check_amount_currency_balance_sign';
        ''')
        constraint = self.env.cr.dictfetchall()
        if constraint:
            self.env.cr.execute("""
                        ALTER TABLE account_move_line DROP CONSTRAINT account_move_line_check_amount_currency_balance_sign;
                    """)


