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
        # Get the last recorded attendance for the employee
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
        ], order='check_in desc', limit=1)

        # Calculate previous calendar week's average
        today = fields.Date.today()
        current_week = today.isocalendar()[1]  # Get current week number
        current_year = today.year
        
        # If we're in week 1, we need to get data from last year's last week
        if current_week == 1:
            last_week = 52
            last_week_year = current_year - 1
        else:
            last_week = current_week - 1
            last_week_year = current_year

        # Get the date for the Monday of the previous week
        last_week_start = datetime.strptime(f'{last_week_year}-W{last_week}-1', '%Y-W%W-%w').date()
        last_week_end = last_week_start + timedelta(days=6)
        
        last_week_attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_in', '>=', last_week_start),
            ('check_in', '<=', last_week_end)
        ])
        
        # Get company's daily work hours and monthly working days
        company = self.env.company
        daily_hours = company.daily_work_hour_dashboard or 9.0
        monthly_working_days = company.monthly_working_days or 22
        
        # Calculate weekly target (5 working days)
        weekly_target = daily_hours * 5
        
        # Calculate monthly target
        monthly_target = daily_hours * monthly_working_days
        
        # Calculate current month's total hours
        current_month_start = today.replace(day=1)
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        current_month_attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_in', '>=', current_month_start),
            ('check_in', '<=', current_month_end)
        ])
        
        # Calculate last week's average
        if last_week_attendances:
            # Group attendances by date
            daily_hours_dict = {}
            for att in last_week_attendances:
                date = att.check_in.date()
                if date not in daily_hours_dict:
                    daily_hours_dict[date] = 0
                daily_hours_dict[date] += att.worked_hours
            
            # Calculate average of daily hours
            total_days = len(daily_hours_dict)
            total_hours = sum(daily_hours_dict.values())
            weekly_average = total_hours / total_days if total_days > 0 else 0
        else:
            weekly_average = 0

        # Calculate monthly total
        monthly_total = sum(current_month_attendances.mapped('worked_hours'))
        
        # Format monthly values
        monthly_hours = int(monthly_total)
        monthly_minutes = int((monthly_total - monthly_hours) * 60)
        monthly_formatted = f"{monthly_hours}h {monthly_minutes}m"
        
        monthly_target_hours = int(monthly_target)
        monthly_target_minutes = int((monthly_target - monthly_target_hours) * 60)
        monthly_target_formatted = f"{monthly_target_hours}h {monthly_target_minutes}m"
        
        # Calculate monthly difference
        monthly_diff = monthly_total - monthly_target
        diff_hours = int(abs(monthly_diff))
        diff_minutes = int((abs(monthly_diff) - diff_hours) * 60)
        monthly_diff_formatted = f"{diff_hours}h {diff_minutes}m"

        if attendance:
            check_in = attendance.check_in.strftime('%H:%M:%S') if attendance.check_in else False
            check_out = attendance.check_out.strftime('%H:%M:%S') if attendance.check_out else False
            # Format worked hours to show hours and minutes
            worked_hours = attendance.worked_hours
            hours = int(worked_hours)
            minutes = int((worked_hours - hours) * 60)
            worked_hours_formatted = f"{hours}h {minutes}m"
            worked_hours_formatted += f" / {int(daily_hours)}h"
        else:
            check_in = check_out = False
            worked_hours_formatted = f"0h 0m / {int(daily_hours)}h"

        # Format weekly average
        weekly_avg_hours = int(weekly_average)
        weekly_avg_minutes = int((weekly_average - weekly_avg_hours) * 60)
        weekly_avg_formatted = f"{weekly_avg_hours}h {weekly_avg_minutes}m"
        
        # Calculate weekly difference from target
        hours_diff = weekly_average - daily_hours
        diff_hours = int(abs(hours_diff))
        diff_minutes = int((abs(hours_diff) - diff_hours) * 60)
        diff_formatted = f"{diff_hours}h {diff_minutes}m"

        # Format date range for display
        date_range = f"Week {last_week} ({last_week_start.strftime('%d %b')} - {last_week_end.strftime('%d %b')})"
        month_range = f"{current_month_start.strftime('%B %Y')}"

        return {
            'check_in': check_in,
            'check_out': check_out,
            'worked_hours': worked_hours_formatted,
            'weekly_average': weekly_avg_formatted,
            'weekly_target': f"{int(weekly_target)}h",
            'meets_target': weekly_average >= daily_hours,
            'hours_diff': diff_formatted,
            'week_date_range': date_range,
            'monthly_total': monthly_formatted,
            'monthly_target': monthly_target_formatted,
            'monthly_meets_target': monthly_total >= monthly_target,
            'monthly_diff': monthly_diff_formatted,
            'month_range': month_range
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
        monthly_data = {}

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

            # Get leaves for the entire year
            taken_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', f'{year}-01-01'),
                ('date_to', '<=', f'{year}-12-31')
            ])

            # Calculate monthly distribution
            monthly_distribution = [0] * 12
            for leave in taken_leaves:
                start_date = leave.date_from
                end_date = leave.date_to
                current_date = start_date
                while current_date <= end_date:
                    if current_date.year == year:
                        month_index = current_date.month - 1
                        monthly_distribution[month_index] += 1
                    current_date += timedelta(days=1)

            available = allocation.number_of_days if allocation else 0
            taken = sum(taken_leaves.mapped('number_of_days'))
            remaining = available - taken

            leaves.append({
                'name': leave_type.name,
                'available': available,
                'taken': taken,
                'remaining': remaining,
                'monthly_data': monthly_distribution
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
