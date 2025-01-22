from odoo import api, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _entry_manager_absent_alert(self):
        nxt_date = self.env.company.absent_manager_nxt_date
        current_date = datetime.now().date()
        if current_date == nxt_date:
            self.env.company.absent_manager_nxt_date = nxt_date + relativedelta(
                days=self.env.company.absent_manager_alert)
            active_managers = self.env["hr.employee"].search([('active', '=', True)]).mapped('parent_id')
            for manager in active_managers:
                employees = self.env["hr.employee"].search([('parent_id', 'child_of', manager.id)])
                employees_with_unprocessed_leaves = []
                for employee in employees:
                    leaves = self.env['tg.leave'].search([
                        ('from_date', '<=', current_date),
                        ('state', '=', 'confirm'),
                        ('is_leave_applied', '=', False),
                        ('employee_id', '=', employee.id)
                    ])
                    for leave in leaves:
                        leave_id = self.env['hr.leave'].search([
                            ('employee_id', '=', leave.employee_id.id),
                            ('request_date_from', '=', leave.from_date)
                        ])
                        if leave_id:
                            leave.is_leave_applied = True
                        else:
                            if employee not in employees_with_unprocessed_leaves:
                                employees_with_unprocessed_leaves.append(employee)
                if employees_with_unprocessed_leaves:
                    # Prepare and send the alert email to the manager
                    context = {
                        'email_to': manager.user_id.email,
                        'email_from': self.env.company.erp_email,
                        'subject': "System Notification: Leave Update Required for Employees",
                        'emp_ids': employees_with_unprocessed_leaves,
                    }
                    template = self.env.ref('tg_holidays.email_template_manager_absent_alert')
                    self.env['mail.template'].browse(template.id).with_context(context).send_mail(manager.id,
                                                                                                  force_send=True)

    def get_absent_dates(self, emp):
        if emp:
            dates = []
            current_date = datetime.now().date()
            absent_leaves = self.env['tg.leave'].search([
                ('from_date', '<=', current_date),
                ('state', '=', 'confirm'),
                ('is_leave_applied', '=', False),
                ('employee_id', '=', emp.id)
            ])

            for leave in absent_leaves:
                # Check if there is no corresponding 'hr.leave' record for this leave
                if not self.env['hr.leave'].search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('request_date_from', '=', leave.from_date)
                ]):
                    dates.append(leave.from_date)

            return dates

    @api.onchange('parent_id')
    def _onchange_manager_approver(self):
        self.leave_manager_id = self.parent_id.user_id.id
