from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AttendanceClaimApproval(models.Model):
    _name = 'attendance.claim.approval'
    _inherit = 'mail.thread'
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
    reclaim_url = fields.Char('Reclaim URL')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='draft', tracking=True)
    show_reclaim = fields.Boolean(default=False)
    is_processed = fields.Boolean(default=False, string="Processed in Attendance")

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
            rec.reclaim_url = f"{base_url}/attendance/reclaim/form?request_id={rec.id}"
            print(rec.reclaim_url )
        return res

    def action_accept(self):
        """Approve claim → update attendance + notify employee"""
        for rec in self:
            day = rec.date_from.date()
            attendance = self.env['hr.attendance'].sudo().search([
                ('fetch_date', '=', day),
                ('employee_id', '=', rec.employee_id.id)
            ], limit=1)

            if not attendance:
                raise ValidationError("No attendance found for this date.")

            # update attendance with approved hours
            attendance.claimed_hours = rec.approved_hour
            attendance.worked_hours += rec.approved_hour
            attendance.actual_hours += rec.approved_hour

            # update claim status
            rec.state = 'accepted'
            rec.is_processed = True

            # send notification email
            template = self.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_status_alert')
            template.send_mail(rec.id, force_send=True)


    def action_reject(self):
        """Reject claim → mark processed + notify employee"""
        for rec in self:
            rec.state = 'rejected'
            rec.show_reclaim = True
            rec.is_processed = True

            template = self.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_status_alert')
            template.send_mail(rec.id, force_send=True)


    @api.model
    def claim_approval_email(self):
        """Cron: notify managers about new (unprocessed) claims"""
        request_ids = self.search([
            ('state', '=', 'draft'),
            ('is_processed', '=', False),
        ])
        for rec in request_ids:
            template = self.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_claim_alert')
            template.send_mail(rec.id, force_send=True)
