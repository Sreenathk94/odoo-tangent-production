from odoo import fields, api, models, _
from odoo.tools import format_datetime
from datetime import datetime, time, timedelta
from pytz import timezone
from odoo.addons.resource.models.utils import make_aware, Intervals
from pytz import timezone, UTC
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta
import calendar
from odoo.tools import date_utils

dubai_tz = timezone('Asia/Dubai')

class LocationMaster(models.Model):
    _name = "hr.location.master"
    _description = "Location Master"
    _order = "id desc"

    name = fields.Char("Room No.")
    detect_lunch = fields.Boolean("Detect Lunch Break",
                                  help="Detect Lunch Break from break hrs else add default 1hr Lunch break.")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    location_id = fields.Many2one("hr.location.master", 'Location')


class HREmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    location_id = fields.Many2one("hr.location.master", 'Location')


class TgAttendance(models.Model):
    _inherit = "hr.attendance"

    line_ids = fields.One2many("hr.attendance.line", 'header_id')
    timesheet_hours = fields.Float("Break Hours", compute='_compute_timesheet_hours', store=True)
    actual_hours = fields.Float("Logged Hours", compute='_compute_actual_hours', store=True)
    check_in = fields.Datetime(string="Check In", required=True)
    check_out = fields.Datetime(string="Check Out", required=True)
    fetch_date = fields.Date(string='Attendance Date', required=True, tracking=True)
    claimed_hours = fields.Float(string='Attendance claimed hours')

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                resource = attendance.employee_id.resource_id
                tz = timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                lunch_intervals = calendar._attendance_intervals_batch(
                    check_in_tz, check_out_tz, resource, lunch=True)
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)])
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)
                temp_worked_hours = delta / 3600.0
                attendance.worked_hours = temp_worked_hours + attendance.claimed_hours if attendance.claimed_hours else temp_worked_hours

            else:
                attendance.worked_hours = False

    @api.depends('line_ids', 'line_ids.worked_hours')
    def _compute_actual_hours(self):
        for rec in self:
            if rec.line_ids:
                rec.actual_hours = sum([x.worked_hours for x in rec.line_ids])
            else:
                rec.actual_hours = 0

    @api.depends('actual_hours', 'timesheet_hours')
    def _compute_timesheet_hours(self):
        for rec in self:
            if rec.actual_hours > 0 and rec.worked_hours > 0:
                rec.timesheet_hours = rec.worked_hours - rec.actual_hours

    @api.model
    def get_unusual_days(self, check_in, check_out=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        dfrom = datetime.combine(fields.Date.from_string(check_in), time.min).replace(tzinfo=UTC)
        dto = datetime.combine(fields.Date.from_string(check_out), time.max).replace(tzinfo=UTC)
        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}

    def float_to_time(self, float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"


    @api.model
    def _employee_alert_daily_attendance(self):
        company = self.env.company
        today = company.fetch_date
        yesterday = today - relativedelta(days=1)
        attendance_ids = self.env['hr.attendance'].search([('fetch_date', '=', yesterday)])

        if today > company.ramadan_start_date and today < company.ramadan_end_date:
            notification_need = attendance_ids.filtered(lambda a: a.actual_hours < company.ramadan_total_work_time)
            com_work_hrs = self.env.company.ramadan_total_work_time
        else:
            notification_need = attendance_ids.filtered(lambda a: a.actual_hours < company.attend_work_hrs)
            com_work_hrs = self.env.company.attend_work_hrs

        for attendance in notification_need:
            data_to_load_html_template = []

            # Convert check-in and check-out times to Asia/Dubai timezone
            check_in_dubai = attendance.check_in.astimezone(dubai_tz)
            check_out_dubai = attendance.check_out.astimezone(dubai_tz)

            data_to_load_html_template.append([
                'First Check-in & Last Check-out',
                check_in_dubai.strftime("%d-%m-%Y %H:%M:%S"),
                check_out_dubai.strftime("%d-%m-%Y %H:%M:%S"),
                "Lunch Break",
                self.float_to_time(attendance.worked_hours),
                ' ', ' '
            ])

            # data_to_load_html_template.append(['Total time excluding break', ' ', ' ', ' ', self.float_to_time(attendance.actual_hours), ' '])

            data_to_load_html_template.append([
                'Breaks', ' ', ' ', ' ', 'Long Break', 'Short Break', ' '
            ])

            start_time = self.env.company.company_start_time
            hours = int(start_time)
            minutes = int((start_time - hours) * 100)

            # Convert start time to Asia/Dubai timezone
            start_time_date = datetime(yesterday.year, yesterday.month, yesterday.day, hours, minutes,
                                       tzinfo=UTC).astimezone(dubai_tz)

            if check_in_dubai > start_time_date:
                start_time_difference = check_in_dubai - start_time_date
                total_late_in_minutes = start_time_difference.total_seconds() // 60
                row = [
                    'Break (Delay)',
                    start_time_date.strftime("%d-%m-%Y %H:%M:%S"),
                    check_in_dubai.strftime("%d-%m-%Y %H:%M:%S"),
                    ' ', ' ', ' ', False
                ]
                if total_late_in_minutes > 15:
                    row[3] = start_time_difference
                    row[6] = 'claim'
                else:
                    row[4] = start_time_difference
                data_to_load_html_template.append(row)

            line_count = 1
            is_first_row = False
            attendance_lines = []
            non_counted = timedelta(days=0)
            counted = timedelta(days=0)
            lunch_break = timedelta(days=0)
            lunch_break_none_counted = timedelta(days=0)
            for line in attendance.line_ids:
                if is_first_row:
                    last_line = attendance_lines[-1]
                    check_in = line.check_in.astimezone(dubai_tz)
                    check_out = last_line[1]
                    if check_out.time() > time(12, 45) and check_out.time() < time(14, 15):
                        dif = check_in - check_out
                        lunch_break += dif
                        if dif > timedelta(hours=1):
                            last_line[3] = str(dif)
                        else:
                            last_line[3] = str(dif)
                            last_line[6] = 'lunch_claim'
                            lunch_break_none_counted = dif - timedelta(hours=1)
                    else:
                        dif = check_in - check_out
                        hours = int(dif.seconds / 3600)
                        minutes = (dif.seconds % 3600) / 60
                        if hours == 0 and minutes <= 15:
                            last_line[5] = str(dif)
                            non_counted += dif
                        else:
                            last_line[4] = str(dif)
                            last_line[6] = 'claim'
                            counted += dif
                    last_line[1] = last_line[1].strftime("%d-%m-%Y %H:%M:%S")
                    last_line[2] = check_in.strftime("%d-%m-%Y %H:%M:%S")
                if line.check_out.astimezone(dubai_tz) != check_out_dubai:
                    attendance_lines.append([
                        f"Break {line_count}",
                        line.check_out.astimezone(dubai_tz),
                        ' ', ' ', ' ', ' ', False
                    ])
                    is_first_row = True
                    line_count += 1
            data_to_load_html_template += attendance_lines

            data_to_load_html_template.append([
                        'Total Breaks', ' ', ' ', str(lunch_break), str(counted), str(non_counted), ' '
                    ])
            to_reduce = non_counted + lunch_break
            worked_hours_td = timedelta(hours=int(attendance.worked_hours),
                                        minutes=(attendance.worked_hours % 1) * 60)

            data_to_load_html_template.append([
                f'Net total time inside the office ({self.float_to_time(attendance.worked_hours)} - { to_reduce }) {worked_hours_td - to_reduce}', ' ', ' ',' ', ' ', ' ', ' '
            ])
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            context = {
                'email_to': 'abhilash.sudhakaran@tangentlandscape.com',
                'email_from': self.env.company.erp_email,
                'sterday': yesterday,
                'base_url': f"{base_url}/attendance/claim/form?date={yesterday.strftime('%d-%b-%Y')}&employee_id={attendance.employee_id.id}",
                'datas': data_to_load_html_template,
                'com_work_hrs': com_work_hrs
            }
            template = self.env.ref('tg_attendance.email_template_employee_daily_attendance_alert')
            template.with_context(context).send_mail(attendance.id, force_send=True)

class Employee(models.Model):
    _inherit = "hr.employee"

    def float_to_time(self, float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    def _employee_weekly_alert_timesheet_attendance(self):
        today = datetime.now().date()
        if today.weekday() == 0:
            start_date = today - relativedelta(days=1)
            last_date = today - relativedelta(days=7)
            emp_ids = self.env['hr.employee'].search([])
            for emp in emp_ids:
                attendance_ids = self.env['hr.attendance'].search(
                    [('employee_id', '=', emp.id), ('fetch_date', '>=', last_date), ('fetch_date', '<=', start_date)])
                if attendance_ids:
                    leave_count = 0
                    leave_days = emp.get_unusual_days_emp(emp.resource_calendar_id, last_date, start_date)
                    leave_count += list(leave_days.values()).count(False)
                    if sum(attendance_ids.mapped('actual_hours')) < (leave_count * self.env.company.attend_work_hrs):
                        avg = sum(attendance_ids.mapped('actual_hours')) / leave_count
                        context = {
                            'email_to': emp.work_email,
                            'email_from': self.env.company.erp_email,
                            'today': start_date,
                            'last_week': last_date,
                            'com_work_hrs': self.float_to_time(self.env.company.attend_work_hrs),
                            'act_work_hrs': self.float_to_time(avg),
                        }
                        template = self.env.ref(
                            'tg_attendance.email_template_employee_weekly_attendance_timesheet_alert')
                        template.with_context(context).send_mail(emp.id, force_send=True)

    def _employee_monthly_alert_timesheet_attendance(self):
        today = fields.date.today()
        previous_month = date_utils.subtract(today, months=1)
        last_day = calendar.monthrange(previous_month.year, previous_month.month)[1]
        start_date = previous_month.replace(day=1, month=previous_month.month, year=previous_month.year)
        last_date = previous_month.replace(day=last_day, month=previous_month.month, year=previous_month.year)
        emp_ids = self.env['hr.employee'].search([])
        for emp in emp_ids:
            attendance_ids = self.env['hr.attendance'].search(
                [('employee_id', '=', emp.id), ('fetch_date', '>=', start_date), ('fetch_date', '<=', last_date)])
            if attendance_ids:
                leave_count = 0
                leave_days = emp.get_unusual_days_emp(emp.resource_calendar_id, start_date, last_date)
                leave_count += list(leave_days.values()).count(False)
                if sum(attendance_ids.mapped('actual_hours')) < (leave_count * self.env.company.attend_work_hrs):
                    avg = sum(attendance_ids.mapped('actual_hours')) / leave_count
                    context = {
                        'email_to': emp.work_email,
                        'email_from': self.env.company.erp_email,
                        'month': previous_month.strftime("%B"),
                        'com_work_hrs': self.env.company.attend_work_hrs,
                        'act_work_hrs': self.float_to_time(avg),
                    }
                    template = self.env.ref('tg_attendance.email_template_employee_monthly_attendance_timesheet_alert')
                    template.with_context(context).send_mail(emp.id, force_send=True)


class TgAttendanceLine(models.Model):
    _name = "hr.attendance.line"
    _description = "Attendance Timesheet"
    _order = "id asc"

    header_id = fields.Many2one("hr.attendance")
    employee_id = fields.Many2one("hr.employee", 'Employee', related='header_id.employee_id', store=True)
    check_in = fields.Datetime("Check In")
    check_out = fields.Datetime("Check Out")
    worked_hours = fields.Float("Logged Hours", compute='_compute_worked_hours', store=True)
    is_permission = fields.Boolean('Permission')

    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((attendance.id, _("%(empl_name)s from %(check_out)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
                }))
            else:
                result.append((attendance.id, _("%(empl_name)s from %(check_out)s to %(check_in)s") % {
                    'empl_name': attendance.employee_id.name,
                    'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
                    'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
                }))
        return result

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = False

    @api.model
    def get_unusual_days(self, check_in, check_out=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        dfrom = datetime.combine(fields.Date.from_string(check_in), time.min).replace(tzinfo=UTC)
        dto = datetime.combine(fields.Date.from_string(check_out), time.max).replace(tzinfo=UTC)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
