from odoo import models, fields, api
from datetime import datetime, timedelta
import calendar


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def get_employee_dashboard_data(self, month=None, year=None):
        # Get the current logged-in employee record
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if not employee:
            return {}

        today = fields.Date.today()

        return {
            'employee_info': employee._get_employee_info(),
            'attendance': employee._get_attendance_data(today),
            'leave': employee._get_leave_data(month, year),
            'projects': employee._get_project_data(),
        }

    def _get_employee_info(self):
        # Use joining_date instead of create_date if available
        joining_date =  self.create_date
        time_since_joining = fields.Date.today() - joining_date.date()
        years = time_since_joining.days // 365
        months = (time_since_joining.days % 365) // 30

        department = self.department_id
        department_info = {
            'name': department.name if department else 'Not Assigned',
            'manager': department.manager_id.name if department and department.manager_id else 'Not Assigned',
            'member_count': len(department.member_ids) if department else 0,
        }

        job = self.job_id
        job_info = {
            'title': job.name if job else 'Not Assigned',
            'description': job.description or ''
        }

        return {
            'name': self.name,
            'image_1920': self.image_1920,
            'job_title': job_info['title'],
            'department': department_info,
            'joining_date': joining_date.strftime('%Y-%m-%d'),
            'time_since_joining': {
                'years': years,
                'months': months
            },
            'work_email': self.work_email,
            'mobile_phone': self.mobile_phone,
            'work_location': self.work_location_id.name if self.work_location_id else '',
            'parent_id': self.parent_id.name if self.parent_id else 'Not Assigned',
            'coach_id': self.coach_id.name if self.coach_id else 'Not Assigned'
        }

    def _get_attendance_data(self, date):
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date, datetime.max.time())

        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_in', '>=', date_start),
            ('check_in', '<=', date_end)
        ], limit=1)

        if attendance:
            check_in = attendance.check_in.strftime('%H:%M:%S') if attendance.check_in else False
            check_out = attendance.check_out.strftime('%H:%M:%S') if attendance.check_out else False
            worked_hours = attendance.worked_hours
        else:
            check_in = check_out = False
            worked_hours = 0.0

        return {
            'check_in': check_in,
            'check_out': check_out,
            'worked_hours': worked_hours
        }

    def _get_leave_data(self, month=None, year=None):
        employee = self

        # Default to current month/year if not provided
        today = fields.Date.today()
        month = int(month) if month else today.month
        year = int(year) if year else today.year

        first_day = fields.Date.to_date(f'{year}-{month:02d}-01')
        last_day = fields.Date.to_date(f'{year}-{month:02d}-{calendar.monthrange(year, month)[1]}')

        leave_types = self.env['hr.leave.type'].search([])
        leaves = []

        for leave_type in leave_types:
            allocation = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', f'{year}-12-31'),
                '|',
                ('date_to', '>=', f'{year}-01-01'),
                ('date_to', '=', False)
            ], limit=1)

            taken_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', first_day),
                ('date_to', '<=', last_day)
            ])

            available = allocation.number_of_days if allocation else 0
            taken = sum(taken_leaves.mapped('number_of_days'))
            remaining = available - taken

            leaves.append({
                'name': leave_type.name,
                'available': available,
                'taken': taken,
                'remaining': remaining
            })

        approved_count = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '>=', first_day),
            ('date_to', '<=', last_day)
        ])

        to_approve_count = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee.id),
            ('state', '=', 'confirm'),
            ('date_from', '>=', first_day),
            ('date_to', '<=', last_day)
        ])

        return {
            'leaves': leaves,
            'approved_count': approved_count,
            'to_approve_count': to_approve_count
        }

    def _get_project_data(self):
        projects = self.env['project.project'].search([
            ('user_id', '=', self.user_id.id)
        ])

        project_data = []
        for project in projects:
            timesheet_entries = self.env['account.analytic.line'].search([
                ('project_id', '=', project.id),
                ('user_id', '=', self.user_id.id)
            ])

            time_spent = sum(timesheet_entries.mapped('unit_amount'))

            project_data.append({
                'id': project.id,
                'name': project.name,
                'time_spent': time_spent,
                'status': 'Active' if project.active else 'Inactive'
            })

        return project_data
