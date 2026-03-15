from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class InstantLeaveRequest(models.Model):
    _name = 'instant.leave.request'
    _description = 'Instant Leave Request'
    _order = 'date desc, id desc'
    _inherit = 'mail.thread'

    name = fields.Char('Reference', required=True, default='New', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date('Leave Date', required=True)
    leave_reason = fields.Text('Leave Reason', required=True)
    applied = fields.Boolean('Leave Applied?', compute='_compute_applied', store=False)
    reporting_manager_id = fields.Many2one(
        'hr.employee', string='Reporting Manager',
        related='employee_id.parent_id', store=True, readonly=True
    )
    notify_employees = fields.Many2many('hr.employee', string='Notify Employees')
    notify_departments = fields.Many2many('hr.department', string='Notify Departments')

    # --------------------------------------------------------
    #  Helper: Check if leave already applied for same date
    # --------------------------------------------------------
    def _has_existing_leave(self):
        """Return True if employee already has validated hr.leave for same date."""
        self.ensure_one()
        employee_leave_applied = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '!=', 'refuse'),
            ('date_from', '=', self.date),
        ], limit=1)
        return bool(employee_leave_applied)

    # --------------------------------------------------------
    @api.depends('employee_id', 'date')
    def _compute_applied(self):
        for rec in self:
            rec.applied = rec._has_existing_leave()

    # --------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('instant.leave.request') or 'New'
        return super().create(vals)

    # --------------------------------------------------------
    def _count_business_days(self, start_date, end_date):
        count = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Mon–Fri
                count += 1
            current_date += timedelta(days=1)
        return count

    # --------------------------------------------------------
    def cron_instant_leaves_reminder(self):
        today = fields.Date.today()
        pending_records = self.search([('applied', '=', False)])

        for rec in pending_records:
            if not rec.date:
                continue
            days_passed = rec._count_business_days(rec.date, today)

            if days_passed >= 3:
                rec._send_employee_reminder()
            if days_passed >= 5:
                rec._send_manager_notification()
            if days_passed >= 8:
                rec._send_hr_escalation()

    # --------------------------------------------------------
    # Email functions (all include "skip if leave exists")
    # --------------------------------------------------------

    def _send_employee_reminder(self):
        self.ensure_one()

        if self._has_existing_leave():
            return  # Skip email

        if not self.employee_id.work_email:
            return

        template = self.env.ref('tg_instant_leave.email_template_employee_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_manager_notification(self):
        self.ensure_one()

        if self._has_existing_leave():
            return  # Skip email

        if not self.reporting_manager_id.work_email:
            return

        template = self.env.ref('tg_instant_leave.email_template_manager_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_hr_escalation(self):
        self.ensure_one()

        if self._has_existing_leave():
            return  # Skip email

        hr_group = self.env.ref('hr_holidays.group_hr_holidays_manager', raise_if_not_found=False)
        if not hr_group:
            return

        hr_users = hr_group.users.filtered(lambda u: u.work_email or u.email)
        if not hr_users:
            return

        hr_emails = ','.join(hr_users.mapped(lambda u: u.work_email or u.email))

        template = self.env.ref('tg_instant_leave.email_template_hr_escalation', raise_if_not_found=False)
        if not template:
            return

        template.with_context(hr_email=hr_emails).send_mail(self.id, force_send=True)

    # --------------------------------------------------------
    def action_notify(self):
        self.ensure_one()

        # -------------------------
        # NEW RULE: DO NOT SEND MAIL IF HR LEAVE EXISTS
        # -------------------------
        # if self._has_existing_leave():
        #     raise UserError(
        #         "Employee has already applied for HR Leave on this date.\n"
        #         "No notification is needed."
        #     )

        # Collect department members
        dept_members = self.notify_departments.mapped('member_ids')

        # All employees to notify
        all_employees = (self.notify_employees | dept_members).filtered('work_email')

        # Team leaders group
        team_group = self.env.ref('tg_instant_leave.group_instant_leave_admin', raise_if_not_found=False)
        leader_users = team_group.users.filtered(lambda u: u.work_email or u.email) if team_group else self.env['res.users']

        # Emails set
        employee_emails = {emp.work_email.strip() for emp in all_employees if emp.work_email}
        leader_emails = {
            (u.work_email or u.email).strip()
            for u in leader_users
            if (u.work_email or u.email)
        }

        emails = employee_emails | leader_emails
        if not emails:
            raise UserError("No valid email recipients found for notification.")

        email_to = ','.join(emails)

        template = self.env.ref('tg_instant_leave.email_template_notify', raise_if_not_found=False)
        if not template:
            raise UserError("Notification email template not found.")

        mail_id = template.send_mail(self.id, force_send=False)
        if not mail_id:
            raise UserError("Failed to generate notification email.")

        # Update and send email
        mail = self.env['mail.mail'].browse(mail_id)
        mail.write({'email_to': email_to, 'auto_delete': False})
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Notification sent to {len(emails)} recipients.',
                'type': 'success',
                'sticky': False,
            }
        }
