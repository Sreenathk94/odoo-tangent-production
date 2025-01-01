from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AttendanceClaimApproval(models.Model):
    _name = 'attendance.claim.approval'
    _description = 'Attendance Claim Approval'
    _order = 'name desc'

    name = fields.Char('Reference')
    employee_id = fields.Many2one('hr.employee', required=True)
    manager_id = fields.Many2one('hr.employee')
    request_hour = fields.Float('Requested Time')
    approved_hour = fields.Float('Approved Time')
    date_from = fields.Datetime(required=True)
    date_to = fields.Datetime(required=True)
    index = fields.Integer()
    reason = fields.Text(required=True)
    note = fields.Text()
    claim_url = fields.Char('URL')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list=vals_list)
        cid = self.env.company.id
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        menu_id = self.env.ref('tg_attendance.menu_attendance_claim_approval').id
        action_id = self.env.ref('tg_attendance.action_attendance_claim_approval').id
        for rec in res:
            rec.name = f'CLM00{rec.id}'
            rec.claim_url = f"{base_url}/web#id={rec.id}&cids={cid}&menu_id={menu_id}&action={action_id}&model=attendance.claim.approval&view_type=form"
        return res

    def action_accept(self):
        day = self.date_from.date()
        header_id = self.env['hr.attendance'].search([
            ('fetch_date', '=', day),
            ('employee_id', '=', self.employee_id.id)
        ])

        header_id.claimed_hours = self.approved_hour
        self.state = 'accepted'

    def action_reject(self):
        self.state = 'rejected'

    @api.model
    def claim_approval_email(self):
        request_ids = self.search([
            ('state', '=', 'draft')
        ])
        for rec in request_ids:
            template = self.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_claim_alert')
            template.send_mail(rec.id, force_send=True)
