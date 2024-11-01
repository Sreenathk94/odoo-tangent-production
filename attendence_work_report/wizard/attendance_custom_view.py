from odoo import models, fields, api
from datetime import datetime, timedelta, time

from odoo.exceptions import UserError


class AttendanceCustomView(models.TransientModel):
    _name = 'attendance.custom.view'
    _description = 'Attendance Custom View Wizard'

    filter_wise = fields.Selection([
        ('today', 'Filter by Today'),
        ('week', 'Filter by Week'),
        ('month', 'Filter by Month'),
        ('custom', 'Filter by Custom Date'),
    ], string='Filter', required=True)

    from_date = fields.Datetime(string='From Date')
    end_date = fields.Datetime(string='End Date')

    def show_report(self):
        """This method filter the hr.attendance records based on the filter"""
        if self.filter_wise == 'today':
            start_time = datetime.combine(datetime.today(), time.min)
            end_time = datetime.combine(datetime.today(), time.max)

        elif self.filter_wise == 'week':
            today = datetime.today()

            # Calculate the start time of the week (Monday) and reduce it by one day
            start_time = datetime.combine(
                today - timedelta(days=today.weekday() + 1),
                time.min)  # Start of the previous week

            # Calculate the end time (Sunday of the current week)
            end_time = datetime.combine(start_time + timedelta(days=6),
                                        time.max)  # E

        elif self.filter_wise == 'month':
            today = datetime.today()
            start_time = datetime.combine(today.replace(day=1),
                                          time.min)  # Start of the month
            next_month = today.replace(day=28) + timedelta(
                days=4)  # This will always result in the next month
            end_time = datetime.combine(
                next_month.replace(day=1) - timedelta(days=1),
                time.max)  # End of the month

        elif self.filter_wise == 'custom':
            if not self.from_date or not self.end_date:
                raise UserError(
                    "Please select both From Date and End Date for custom filter.")
            start_time = datetime.combine(self.from_date, time.min)
            end_time = datetime.combine(self.end_date, time.max)

        else:
            raise UserError("Invalid filter option selected.")

        # Search for records within the calculated date range
        print(start_time, end_time)
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_hr_attendance_action',
            'context': {
                "start_time": start_time,
                "end_time": end_time
            },
        }
