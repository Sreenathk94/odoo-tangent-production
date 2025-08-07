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

# Lunch hour window (no claim inside this period)
LUNCH_START = time(13, 0)  # 1:00 PM
LUNCH_END = time(14, 0)    # 2:00 PM

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
    """
    Cron job to send daily attendance alerts.
    - Checks attendance for the previous day.
    - Calculates breaks (claims vs short) while excluding 1:00–2:00 PM lunch hour.
    """

    _logger.info("Starting daily attendance alert cron job...")

    today = self.env.company.fetch_date
    yesterday = today - relativedelta(days=1)

    _logger.info("Processing attendance for: %s", yesterday)

    # Prepare lunch window datetimes
    lunch_start_dt = dubai_tz.localize(datetime.combine(yesterday, LUNCH_START))
    lunch_end_dt = dubai_tz.localize(datetime.combine(yesterday, LUNCH_END))
    default_lunch = timedelta(hours=1)

    attendance_ids = self.env['hr.attendance'].search([('fetch_date', '=', yesterday)])
    _logger.info("Found %d attendance records", len(attendance_ids))

    notification_need = attendance_ids.filtered(
        lambda a: a.actual_hours < self.env.company.attend_work_hrs
    )
    _logger.info("%d employees have actual hours less than required", len(notification_need))

    for attendance in notification_need:
        _logger.info("Processing employee: %s", attendance.employee_id.name)
        data_to_load_html_template = []

        check_in_dubai = attendance.check_in.astimezone(dubai_tz)
        check_out_dubai = attendance.check_out.astimezone(dubai_tz)

        _logger.debug("Check-in: %s, Check-out: %s", check_in_dubai, check_out_dubai)

        data_to_load_html_template.append([
            'First Check-in & Last Check-out',
            check_in_dubai.strftime("%d-%m-%Y %H:%M:%S"),
            check_out_dubai.strftime("%d-%m-%Y %H:%M:%S"),
            "Lunch Break",
            self.float_to_time(attendance.worked_hours),
            ' ', ' '
        ])

        data_to_load_html_template.append([
            'Breaks', ' ', ' ', ' ', 'Long Break', 'Short Break', ' '
        ])

        start_time = self.env.company.company_start_time
        hours = int(start_time)
        minutes = int((start_time - hours) * 100)
        start_time_date = dubai_tz.localize(datetime(
            yesterday.year, yesterday.month, yesterday.day, hours, minutes
        ))

        if check_in_dubai > start_time_date:
            start_time_difference = check_in_dubai - start_time_date
            total_late_in_minutes = start_time_difference.total_seconds() // 60
            _logger.debug("Late check-in detected: %s minutes", total_late_in_minutes)

            row = [
                'Break (Delay)',
                start_time_date.strftime("%d-%m-%Y %H:%M:%S"),
                check_in_dubai.strftime("%d-%m-%Y %H:%M:%S"),
                ' ', ' ', ' ', False
            ]
            if total_late_in_minutes > 15:
                row[4] = start_time_difference
                row[6] = 'claim'
            else:
                row[5] = start_time_difference
            data_to_load_html_template.append(row)

        line_count = 1
        is_first_row = False
        attendance_lines = []
        non_counted = timedelta(0)
        counted = timedelta(0)
        extra_lunch = timedelta(0)
        actual_lunch = timedelta(0)

        for line in attendance.line_ids:
            if is_first_row:
                last_line = attendance_lines[-1]
                check_in = line.check_in.astimezone(dubai_tz)
                check_out = last_line[1]
                dif = check_in - check_out

                lunch_part = timedelta(0)
                pre_lunch_part = timedelta(0)
                post_lunch_part = timedelta(0)

                if check_out < lunch_start_dt and check_in <= lunch_start_dt:
                    pre_lunch_part = dif
                elif check_out >= lunch_end_dt and check_in > lunch_end_dt:
                    post_lunch_part = dif
                elif check_out >= lunch_start_dt and check_in <= lunch_end_dt:
                    lunch_part = dif
                elif check_out < lunch_start_dt < check_in <= lunch_end_dt:
                    pre_lunch_part = lunch_start_dt - check_out
                    lunch_part = check_in - lunch_start_dt
                elif lunch_start_dt <= check_out < lunch_end_dt < check_in:
                    lunch_part = lunch_end_dt - check_out
                    post_lunch_part = check_in - lunch_end_dt
                elif check_out < lunch_start_dt and check_in > lunch_end_dt:
                    pre_lunch_part = lunch_start_dt - check_out
                    lunch_part = lunch_end_dt - lunch_start_dt
                    post_lunch_part = check_in - lunch_end_dt

                if lunch_part > timedelta(0):
                    actual_lunch += lunch_part
                    last_line[3] = str(lunch_part)

                if pre_lunch_part > timedelta(0):
                    if pre_lunch_part >= timedelta(minutes=15):
                        last_line[4] = str(pre_lunch_part)
                        last_line[6] = 'claim'
                        counted += pre_lunch_part
                    else:
                        last_line[5] = str(pre_lunch_part)
                        non_counted += pre_lunch_part

                if post_lunch_part > timedelta(0):
                    if post_lunch_part >= timedelta(minutes=15):
                        last_line[4] = str(post_lunch_part)
                        last_line[6] = 'claim'
                        counted += post_lunch_part
                    else:
                        last_line[5] = str(post_lunch_part)
                        non_counted += post_lunch_part

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

        if actual_lunch > default_lunch:
            extra_lunch = actual_lunch - default_lunch
            _logger.debug("Extra lunch taken: %s", extra_lunch)

        total_presence = check_out_dubai - check_in_dubai
        total_breaks = counted + non_counted + extra_lunch + default_lunch
        net_time = total_presence - total_breaks

        _logger.debug("Total presence: %s, Breaks: %s, Net time: %s", total_presence, total_breaks, net_time)

        data_to_load_html_template.append([
            'Total Breaks', ' ', ' ', str(actual_lunch), str(counted), str(non_counted), ' '
        ])
        data_to_load_html_template.append([
            f'Estimated Productive Hours ({total_presence} - {total_breaks}) {net_time}',
            ' ', ' ', ' ', ' ', ' ', ' '
        ])
        data_to_load_html_template.append([' ', ' ', ' ', ' ', ' ', ' ', ' '])
        data_to_load_html_template.append([
            'Breaks Taken During Lunch Period(1PM-2PM)',
            str(actual_lunch),
            '1 Hour Default deduction',
            ' ', ' ', ' ', ' '
        ])
        data_to_load_html_template.append([
            'Break balance during lunch break',
            default_lunch - actual_lunch,
            ' ',' ', ' ', ' ', ' '
        ])
        data_to_load_html_template.append([
            'Long Break+Short Break',
            str(counted + non_counted),
            ' ', ' ', ' ', ' ', ' '
        ])
        data_to_load_html_template.append([
            'Total Break including Lunch 1 hour',
            str(counted + non_counted),
            str(default_lunch),
            str(total_breaks),
            ' ', ' ', ' '
        ])
        data_to_load_html_template.append([
            'Productive Hours of the Day',
            str(net_time),
            ' ', ' ', ' ', ' ', ' '
        ])

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        context = {
            'email_to' : attendance.employee_id.work_email,
            'email_from': self.env.company.erp_email,
            'sterday': yesterday,
            'base_url': f"{base_url}/attendance/claim/form?date={yesterday.strftime('%d-%b-%Y')}&employee_id={attendance.employee_id.id}",
            'datas': data_to_load_html_template,
            'com_work_hrs': self.env.company.attend_work_hrs
        }

        _logger.info("Sending attendance alert to: %s", attendance.employee_id.work_email)

        template = self.env.ref('tg_attendance.email_template_employee_daily_attendance_alert')
        template.with_context(context).send_mail(attendance.id, force_send=True)

    _logger.info("Completed daily attendance alert cron job.")

    def _classify_break(self, duration):
        """Classify a break based on the 15-minute rule."""
        return 'claim' if duration >= timedelta(minutes=15) else 'short'

class Employee(models.Model):
    _inherit = "hr.employee"

    def float_to_time(self, float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"


    def _employee_weekly_alert_timesheet_attendance(self):
        today = datetime.now().date()

        # Calculate last week's Sunday and Saturday
        weekday = today.weekday()  # Monday=0 ... Sunday=6
        last_saturday = today - timedelta(days=weekday + 2)  # Go back to last Saturday
        last_sunday = last_saturday - timedelta(days=6)

        emp_ids = self.env['hr.employee'].search([])
        for emp in emp_ids:
            attendance_ids = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('fetch_date', '>=', last_sunday),
                ('fetch_date', '<=', last_saturday)
            ])
            if attendance_ids:
                leave_count = 0
                leave_days = emp.get_unusual_days_emp(emp.resource_calendar_id, last_sunday, last_saturday)
                leave_count += list(leave_days.values()).count(False)

                if sum(attendance_ids.mapped('actual_hours')) < (leave_count * self.env.company.attend_work_hrs):
                    avg = sum(attendance_ids.mapped('actual_hours')) / leave_count
                    context = {
                        'email_to': emp.work_email,
                        'email_from': self.env.company.erp_email,
                        'today': last_saturday,
                        'last_week': last_sunday,
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
