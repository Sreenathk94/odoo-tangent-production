from odoo import api, models
from datetime import datetime,timedelta
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
        sick_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SL')], limit=1)

        if not leave_type or leave_type.request_unit != 'hour' or not sick_leave_type:
            return

        today = date.today()
        current_month_start = today.replace(day=1)
        six_months_ago = today - relativedelta(months=6)

        # --- PART 1: Monthly accrual during probation ---
        probation_employees = self.search([
            ('date_of_join', '>=', six_months_ago),
            ('date_of_join', '<=', today),
            ('resource_calendar_id', '=', 3)
        ])

        for employee in probation_employees:
            # Annual Leave Check and Allocation
            existing_annual = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type.id),
                ('is_probation_accrual', '=', True),
                ('create_date', '>=', current_month_start),
            ], limit=1)

            if not existing_annual:
                self.env['hr.leave.allocation'].create({
                    'name': f'Probation Monthly UAE AL ({today.strftime("%B %Y")}-{employee.name})',
                    'employee_id': employee.id,
                    'employee_ids': [(6, 0, [employee.id])],
                    'holiday_status_id': leave_type.id,
                    'number_of_days': 1.833333333333333,
                    'allocation_type': 'regular',
                    'is_probation_accrual': True,
                    'date_to': date(today.year, 12, 31),
                })

            # Sick Leave Check and Allocation
            existing_sick = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', sick_leave_type.id),
                ('is_probation_sl_allocation', '=', True),
                ('create_date', '>=', current_month_start),
            ], limit=1)

            if not existing_sick:
                self.env['hr.leave.allocation'].create({
                    'name': f'Probation Monthly UAE SL ({today.strftime("%B %Y")}-{employee.name})',
                    'employee_id': employee.id,
                    'employee_ids': [(6, 0, [employee.id])],
                    'holiday_status_id': sick_leave_type.id,
                    'number_of_days': 1.0,  # Assuming 1 sick day = 9 hours
                    'allocation_type': 'regular',
                    'is_probation_sl_allocation': True,
                    'date_to': date(today.year, 12, 31),
                })

        # --- PART 2: Pro-rated annual leave post probation completion ---
        post_probation_employees = self.search([
            ('date_of_join', '!=', False),
            ('resource_calendar_id', '=', 3)
        ])

        for employee in post_probation_employees:
            probation_end_date = employee.date_of_join + relativedelta(months=6)
            if today - timedelta(days=3) <= probation_end_date <= today:
                continue

            # Annual Leave for Remaining Year
            existing_post_alloc = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', leave_type.id),
                ('is_post_probation_allocation', '=', True),
            ], limit=1)

            if not existing_post_alloc:
                months_remaining = 12 - probation_end_date.month
                if months_remaining > 0:
                    self.env['hr.leave.allocation'].create({
                        'name': f'Post-Probation UAE Annual Allocation ({today.year}-{employee.name})',
                        'employee_id': employee.id,
                        'employee_ids': [(6, 0, [employee.id])],
                        'holiday_status_id': leave_type.id,
                        'number_of_days': 1.833333333333333 * months_remaining,
                        'allocation_type': 'regular',
                        'is_post_probation_allocation': True,
                        'date_to': date(today.year, 12, 31),
                    })


            # Sick Leave: Top up to 12 days
            existing_sick_allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
                ('holiday_status_id', '=', sick_leave_type.id),
                ('date_from', '>=', date(today.year, 1, 1)),
                ('date_to', '<=', date(today.year, 12, 31))
            ])

            total_allocated_hours = sum(existing_sick_allocations.mapped('number_of_days')) * 9
            remaining_hours = max(0, (12 * 9) - total_allocated_hours)

            if remaining_hours > 0:
                self.env['hr.leave.allocation'].create({
                    'name': f'Sick Leave Top-Up ({today.year}-{employee.name})',
                    'employee_id': employee.id,
                    'employee_ids': [(6, 0, [employee.id])],
                    'holiday_status_id': sick_leave_type.id,
                    'number_of_days': remaining_hours / 9,
                    'allocation_type': 'regular',
                    'is_sick_leave_allocation': True,
                    'date_to': date(today.year, 12, 31),
                })

    def _accrue_indian_user_probation_leave(self):
        sick_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SL')], limit=1)
        special_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SPL')], limit=1)
        festive_leave_type = self.env['hr.leave.type'].search([('code', '=', 'FL')], limit=1)

        if not sick_leave_type or not special_leave_type or not festive_leave_type:
            return

        today = date.today()
        current_month_start = today.replace(day=1)
        six_months_ago = today - relativedelta(months=6)

        # --- PART 1: Monthly accrual during probation ---
        probation_employees = self.search([
            ('date_of_join', '>=', six_months_ago),
            ('date_of_join', '<=', today),
            ('resource_calendar_id', '=', 2)
        ])
        for employee in probation_employees:
            for leave_type, code, label in [
                (sick_leave_type, 'SL', 'Sick Leave'),
                (special_leave_type, 'SPL', 'Special Leave'),
                (festive_leave_type, 'FL', 'Personal Festive Leave'),
            ]:
                field_flag = f'is_probation_{code.lower()}_allocation'
                existing = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '!=', 'refuse'),
                    ('holiday_status_id', '=', leave_type.id),
                    (field_flag, '=', True),
                    ('create_date', '>=', current_month_start),
                ], limit=1)

                if existing:
                    continue

                # ✅ Cap festive leave to max 2 days in a year
                max_allowed = 1.0
                if code == 'FL':
                    festive_allocs = self.env['hr.leave.allocation'].search([
                        ('employee_id', '=', employee.id),
                        ('state', '!=', 'refuse'),
                        ('holiday_status_id', '=', festive_leave_type.id),
                        ('date_from', '>=', date(today.year, 1, 1)),
                        ('date_to', '<=', date(today.year, 12, 31)),
                    ])
                    festive_days_allocated = sum(festive_allocs.mapped('number_of_days'))
                    if festive_days_allocated >= 2.0:
                        continue  # Skip allocation
                    max_allowed = min(1.0, 2.0 - festive_days_allocated)

                self.env['hr.leave.allocation'].create({
                    'name': f'Probation Monthly {label} (Indian - {today.strftime("%B %Y")}-{employee.name})',
                    'employee_id': employee.id,
                    'employee_ids': [(6, 0, [employee.id])],
                    'holiday_status_id': leave_type.id,
                    'number_of_days': max_allowed,
                    'allocation_type': 'regular',
                    field_flag: True,
                    'notes': f'Indian Probation Monthly {label} Allocation',
                    'date_to': date(today.year, 12, 31),
                })

        # --- PART 2: Post-Probation Top-up allocation ---
        post_probation_employees = self.search([
            ('date_of_join', '!=', False),
            ('resource_calendar_id', '=', 2)
        ])

        for employee in post_probation_employees:
            probation_end_date = employee.date_of_join + relativedelta(months=6)
            if today - timedelta(days=3) <= probation_end_date <= today:
                continue

            for leave_type, total_days, code, label in [
                (sick_leave_type, 6, 'SL', 'Sick Leave'),
                (special_leave_type, 6, 'SPL', 'Special Leave'),
                (festive_leave_type, 2, 'FL', 'Personal Festive Leave'),  # ✅ Max 2 days
            ]:
                existing_allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '!=', 'refuse'),
                    ('holiday_status_id', '=', leave_type.id),
                    ('date_from', '>=', date(today.year, 1, 1)),
                    ('date_to', '<=', date(today.year, 12, 31))
                ])
                total_allocated_hours = sum(existing_allocations.mapped('number_of_days')) * 9
                remaining_hours = max(0, (total_days * 9) - total_allocated_hours)

                if remaining_hours > 0:
                    self.env['hr.leave.allocation'].create({
                        'name': f'{label} Top-Up (Indian - {today.year}-{employee.name})',
                        'employee_id': employee.id,
                        'employee_ids': [(6, 0, [employee.id])],
                        'holiday_status_id': leave_type.id,
                        'number_of_days': remaining_hours / 9,
                        'allocation_type': 'regular',
                        f'is_{code.lower()}_leave_allocation': True,
                        'notes': (
                            f'Indian user post-probation {label} top-up.\n'
                            f'Already allocated: {total_allocated_hours / 9:.2f} days. '
                            f'Topped up to reach {total_days} days.'
                        ),
                        'date_to': date(today.year, 12, 31),
                    })

    def _allocate_annual_leave_post_probation(self):
        annual_leave_type = self.env['hr.leave.type'].search([('code', '=', 'AL')], limit=1)
        sick_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SL')], limit=1)

        if not annual_leave_type or not sick_leave_type:
            return

        today = date.today()
        end_of_year = date(today.year, 12, 31)
        probation_cutoff = today - relativedelta(months=6)

        eligible_employees = self.search([
            ('date_of_join', '!=', False),
            ('date_of_join', '<=', probation_cutoff),
            ('resource_calendar_id', '=', 3)
        ])

        employees_to_allocate = []

        for emp in eligible_employees:
            # Check if already allocated annual leave this year
            existing = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', annual_leave_type.id),
                ('is_annual_allocation', '=', True),
                ('create_date', '>=', date(today.year, 1, 1)),
            ], limit=1)

            if not existing:
                employees_to_allocate.append(emp.id)

            # --- Carry Forward Logic (max 7 days total from both AL and SL) ---
            last_year = today.year - 1

            def get_leave_data(leave_type):
                allocs = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('create_date', '<', date(today.year, 1, 1)),
                ])
                used = self.env['hr.leave'].search_read([
                    ('employee_ids', 'in', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '>=', date(last_year, 1, 1)),
                    ('request_date_to', '<=', date(last_year, 12, 31)),
                ], ['number_of_hours'])

                total_allocated = sum(
                    a.number_of_days * 9 for a in allocs if a.holiday_status_id.request_unit == 'hour')
                total_used = sum(l['number_of_hours'] for l in used)
                remaining = max(0, total_allocated - total_used)
                return remaining, total_allocated, total_used

            al_remaining, al_total_allocated, al_total_used = get_leave_data(annual_leave_type)
            sl_remaining, sl_total_allocated, sl_total_used = get_leave_data(sick_leave_type)

            total_remaining_hours = al_remaining + sl_remaining
            carry_forward_hours = min(63, total_remaining_hours)  # 7 days * 9 hours

            if carry_forward_hours > 0:
                note = (
                    f"Carry Forward Calculation:\n"
                    f"Annual Leave Remaining: {al_remaining} hrs (Allocated: {al_total_allocated}, Used: {al_total_used})\n"
                    f"Sick Leave Remaining: {sl_remaining} hrs (Allocated: {sl_total_allocated}, Used: {sl_total_used})\n"
                    f"Total Remaining: {total_remaining_hours} hrs\n"
                    f"Carried Forward: {carry_forward_hours} hrs (Max 7 days / 63 hrs)"
                )

                self.env['hr.leave.allocation'].create({
                    'name': f'Carry Forward UAE Leave ({today.year})',
                    'employee_id': emp.id,
                    'employee_ids': [(6, 0, [emp.id])],
                    'holiday_status_id': annual_leave_type.id,
                    'number_of_days': carry_forward_hours / 9,
                    'allocation_type': 'regular',
                    'is_carry_forward': True,
                    'notes': note,
                    'date_to': end_of_year,
                })

        # Allocate Annual Leave for current year
        if employees_to_allocate:
            self.env['hr.leave.allocation'].create({
                'name': f'Annual Leave UAE Allocation ({today.year})',
                'employee_id': employees_to_allocate[0],
                'employee_ids': [(6, 0, employees_to_allocate)],
                'holiday_status_id': annual_leave_type.id,
                'number_of_days': 22,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
                'is_annual_allocation': True,
                'date_to': end_of_year,
            })

            # Allocate Sick Leave (12 days = 108 hrs)
            self.env['hr.leave.allocation'].create({
                'name': f'Sick Leave UAE Allocation ({today.year})',
                'employee_id': employees_to_allocate[0],
                'employee_ids': [(6, 0, employees_to_allocate)],
                'holiday_status_id': sick_leave_type.id,
                'number_of_days': 12,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
                'is_sick_allocation': True,
                'date_to': end_of_year,
            })

    def _allocate_indian_leave_post_probation(self):
        sick_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SL')], limit=1)
        special_leave_type = self.env['hr.leave.type'].search([('code', '=', 'SPL')], limit=1)
        festive_leave_type = self.env['hr.leave.type'].search([('code', '=', 'FL')], limit=1)

        if not sick_leave_type or not special_leave_type or not festive_leave_type:
            return

        today = date.today()
        end_of_year = date(today.year, 12, 31)
        probation_cutoff = today - relativedelta(months=6)

        eligible_employees = self.search([
            ('date_of_join', '!=', False),
            ('date_of_join', '<=', probation_cutoff),
            ('resource_calendar_id', '=', 2)
        ])

        employees_to_allocate = []

        for emp in eligible_employees:
            existing = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', sick_leave_type.id),
                ('is_annual_allocation', '=', True),
                ('create_date', '>=', date(today.year, 1, 1)),
            ], limit=1)

            if not existing:
                employees_to_allocate.append(emp.id)

            # --- Carry Forward Logic (max 7 days / 63 hours total for all 3 leave types) ---
            last_year = today.year - 1

            def get_leave_data(leave_type):
                allocs = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('create_date', '<', date(today.year, 1, 1)),
                ])
                used = self.env['hr.leave'].search_read([
                    ('employee_ids', 'in', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '>=', date(last_year, 1, 1)),
                    ('request_date_to', '<=', date(last_year, 12, 31)),
                ], ['number_of_hours'])

                total_allocated = sum(
                    a.number_of_days * 9 for a in allocs if a.holiday_status_id.request_unit == 'hour')
                total_used = sum(l['number_of_hours'] for l in used)
                remaining = max(0, total_allocated - total_used)
                return remaining, total_allocated, total_used

            sl_remaining, sl_alloc, sl_used = get_leave_data(sick_leave_type)
            spl_remaining, spl_alloc, spl_used = get_leave_data(special_leave_type)
            fl_remaining, fl_alloc, fl_used = get_leave_data(festive_leave_type)

            total_remaining_hours = sl_remaining + spl_remaining + fl_remaining
            carry_forward_hours = min(63, total_remaining_hours)  # max 7 days * 9 hours

            if carry_forward_hours > 0:
                note = (
                    f"Indian Leave Carry Forward Calculation:\n"
                    f"Sick Leave Remaining: {sl_remaining} hrs (Allocated: {sl_alloc}, Used: {sl_used})\n"
                    f"Special Leave Remaining: {spl_remaining} hrs (Allocated: {spl_alloc}, Used: {spl_used})\n"
                    f"Festive Leave Remaining: {fl_remaining} hrs (Allocated: {fl_alloc}, Used: {fl_used})\n"
                    f"Total Remaining: {total_remaining_hours} hrs\n"
                    f"Carried Forward: {carry_forward_hours} hrs (Max 7 days / 63 hrs)"
                )

                self.env['hr.leave.allocation'].create({
                    'name': f'Carry Forward Indian Leave ({today.year})',
                    'employee_id': emp.id,
                    'employee_ids': [(6, 0, [emp.id])],
                    'holiday_status_id': sick_leave_type.id,  # Logically using SL to store it
                    'number_of_days': carry_forward_hours / 9,
                    'allocation_type': 'regular',
                    'is_carry_forward': True,
                    'notes': note,
                    'date_to': end_of_year,
                })

        if employees_to_allocate:
            self.env['hr.leave.allocation'].create({
                'name': f'Indian Sick Leave Allocation ({today.year})',
                'employee_id': employees_to_allocate[0],
                'employee_ids': [(6, 0, employees_to_allocate)],
                'holiday_status_id': sick_leave_type.id,
                'number_of_days': 6,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
                'is_annual_allocation': True,
                'notes': 'Indian Sick Leave Allocation after probation',
                'date_to': end_of_year,
            })

            self.env['hr.leave.allocation'].create({
                'name': f'Indian Special Leave Allocation ({today.year})',
                'employee_id': employees_to_allocate[0],
                'employee_ids': [(6, 0, employees_to_allocate)],
                'holiday_status_id': special_leave_type.id,
                'number_of_days': 6,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
                'is_special_allocation': True,
                'notes': 'Indian Special Leave Allocation after probation',
                'date_to': end_of_year,
            })

            self.env['hr.leave.allocation'].create({
                'name': f'Indian Festive Leave Allocation ({today.year})',
                'employee_id': employees_to_allocate[0],
                'employee_ids': [(6, 0, employees_to_allocate)],
                'holiday_status_id': festive_leave_type.id,
                'number_of_days': 2,
                'allocation_type': 'regular',
                'is_post_probation_allocation': True,
                'is_festive_allocation': True,
                'notes': 'Indian Festive Leave Allocation after probation',
                'date_to': end_of_year,
            })





