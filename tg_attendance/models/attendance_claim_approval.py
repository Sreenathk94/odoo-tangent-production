from odoo import models, fields, api


class AttendanceClaimApproval(models.Model):
    _name = 'attendance.claim.approval'
    _description = 'Attendance Claim Approval'

    name = fields.Char('Reference')
    employee_id = fields.Many2one('hr.employee', required=True)
    manager_id = fields.Many2one('hr.employee')

    date_from = fields.Datetime(required=True)
    date_to = fields.Datetime(required=True)

    reason = fields.Text(required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list=vals_list)
        for rec in res:
            rec.name = f'CLM00{rec.id}'
        return res

    def action_accept(self):
        day = self.date_from.date()
        header_id = self.env['hr.attendance'].search([
            ('fetch_date', '=', day),
            ('employee_id', '=', self.employee_id.id)
        ])
        self.env['hr.attendance.line'].create({
            'header_id': header_id.id,
            'employee_id': self.employee_id.id,
            'check_out': self.date_to,
            'check_in': self.date_from
        })
        self.state = 'accepted'

    def action_reject(self):
        self.state = 'rejected'
