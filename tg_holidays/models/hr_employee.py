from odoo import api, models
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import date


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

    def _accrue_daily_probation_leave(self):
        leave_type = self.env['hr.leave.type'].search([('code', '=', 'AL')], limit=1)
        if not leave_type or leave_type.request_unit != 'hour':
            return

        today = date.today()
        current_month_start = today.replace(day=1)
        six_months_ago = today - relativedelta(months=6)

        # --- PART 1: Monthly accrual during probation ---
        probation_employees = self.search([
            ('date_of_join', '>=', six_months_ago),
            ('date_of_join', '<=', today),
            ('location_id', '!=', 3)
        ])

        for employee in probation_employees:
            existing_allocation = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type.id),
                ('is_probation_accrual', '=', True),
                ('create_date', '>=', current_month_start),
            ], limit=1)

            if not existing_allocation:
                self.env['hr.leave.allocation'].create({
                    'name': f'Probation Monthly Allocation ({today.strftime("%B %Y")}-{employee.name})',
                    'employee_id': employee.id,
                    'employee_ids': [(6, 0, [employee.id])],
                    'holiday_status_id': leave_type.id,
                    'number_of_days': 1.83,
                    'allocation_type': 'regular',
                    'is_probation_accrual': True,
                })

        # --- PART 2: Pro-rated annual leave post probation completion ---
        post_probation_employees = self.search([
            ('date_of_join', '!=', False),('location_id', '!=', 3)
        ])

        for employee in post_probation_employees:
            probation_end_date = employee.date_of_join + relativedelta(months=6)
            if probation_end_date != today:
                continue

            existing_post_alloc = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type.id),
                ('is_post_probation_allocation', '=', True),
            ], limit=1)

            if existing_post_alloc:
                continue

            # Leave accrual for remaining months (excluding the probation end month)
            months_remaining = 12 - probation_end_date.month

            if months_remaining <= 0:
                continue  # No allocation needed
            self.env['hr.leave.allocation'].create({
                'name': f'Post-Probation Annual Allocation ({today.year}-{employee.name})',
                'employee_id': employee.id,
                'employee_ids': [(6, 0, [employee.id])],
                'holiday_status_id': leave_type.id,
                'number_of_days': 1.83 * months_remaining,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
            })

    def _allocate_annual_leave_post_probation(self):
        leave_type = self.env['hr.leave.type'].search([('code', '=', 'AL')], limit=1)
        if not leave_type or leave_type.request_unit != 'hour':
            return

        today = date.today()
        probation_cutoff = today - relativedelta(months=6)

        eligible_employees = self.search([
            ('date_of_join', '!=', False),
            ('date_of_join', '<=', probation_cutoff),
            ('location_id', '!=', 3)
        ])

        # Filter out employees who already received an annual allocation this year
        employees_to_allocate = []
        for emp in eligible_employees:
            existing = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', leave_type.id),
                ('is_annual_allocation', '=', True),
                ('create_date', '>=', today.replace(month=1, day=1)),
            ], limit=1)
            if not existing:
                employees_to_allocate.append(emp.id)

        if not employees_to_allocate:
            return

        # Create a single batch allocation
        self.env['hr.leave.allocation'].create({
            'name': f'Annual Leave Allocation ({today.year})',
            'employee_id': 118,
            'employee_ids': [(6, 0, employees_to_allocate)],
            'holiday_status_id': leave_type.id,
            'number_of_days':  22,
            'allocation_type': 'regular',
            'is_post_probation_allocation': True,
        })

