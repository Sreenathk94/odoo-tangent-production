from odoo import fields,api,models,_
from odoo.tools import format_datetime
from datetime import datetime,time,timedelta
from pytz import timezone
from odoo.addons.resource.models.utils import make_aware, Intervals
from pytz import UTC
import pytz
from dateutil.rrule import rrule, DAILY
import xlwt
import base64
from io import BytesIO
from dateutil.relativedelta import relativedelta
import calendar
from odoo.tools import date_utils

class LocationMaster(models.Model):
	_name = "hr.location.master"
	_description = "Location Master"
	_order = "id desc"

	name = fields.Char("Room No.")
	detect_lunch = fields.Boolean("Detect Lunch Break",
		help="Detect Lunch Break from break hrs else add default 1hr Lunch break.")

class HrEmployee(models.Model):
	_inherit = "hr.employee"

	location_id = fields.Many2one("hr.location.master",'Location')
	
class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"
	
	location_id = fields.Many2one("hr.location.master",'Location')

class TgAttendance(models.Model):
	_inherit = "hr.attendance"

	line_ids = fields.One2many("hr.attendance.line",'header_id')
	timesheet_hours = fields.Float("Break Hours",compute='_compute_timesheet_hours',store=True)
	actual_hours = fields.Float("Logged Hours",compute='_compute_actual_hours',store=True)
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
				attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals[
					resource.id]
				delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)
				temp_worked_hours = delta / 3600.0
				attendance.worked_hours = temp_worked_hours + attendance.claimed_hours if attendance.claimed_hours else temp_worked_hours

			else:
				attendance.worked_hours = False

	@api.depends('line_ids','line_ids.worked_hours')
	def _compute_actual_hours(self):
		for rec in self:
			if rec.line_ids:
				rec.actual_hours = sum([x.worked_hours for x in rec.line_ids])
			else:
				rec.actual_hours = 0

	@api.depends('actual_hours','timesheet_hours')
	def  _compute_timesheet_hours(self):
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

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int(round((float_value - hours) * 60))
		return f"{hours:02d}:{minutes:02d}"

	def get_native_time(self, time_in_utc, employee_tz):
		utc_tz = pytz.utc
		return time_in_utc.replace(tzinfo=employee_tz).astimezone(utc_tz).replace(
			tzinfo=None) + timedelta(minutes=19)


	@api.model
	def _employee_alert_daily_attendance(self):
		today = self.env.company.fetch_date
		sterday = today - relativedelta(days=1)
		for attendance in self.env['hr.attendance'].search([('fetch_date','=',sterday)]).filtered(lambda a: a.actual_hours < self.env.company.attend_work_hrs):
			# Set Asia/Dubai timezone and UTC timezone
			employee_tz = pytz.timezone(attendance.employee_id.user_id.tz)
			check_in_utc_naive = self.get_native_time(attendance.check_in, employee_tz)
			check_out_utc_naive = self.get_native_time(attendance.check_out, employee_tz)
			data_to_load_html_template = []

			i=4;j=1;k=len(attendance.line_ids)
			total_time_in_office = check_out_utc_naive - check_in_utc_naive

			total_seconds = total_time_in_office.total_seconds()
			hours = int(total_seconds // 3600)  # Get the total hours
			minutes = int((total_seconds % 3600) // 60)

			data_to_load_html_template.append([
				'First Check-in & Last Check-out',
				check_in_utc_naive.strftime("%d-%m-%Y %H:%M:%S"),
				check_out_utc_naive.strftime("%d-%m-%Y %H:%M:%S"),
				f"{hours:02d}:{minutes:02d}",
				' ',
			])
			if attendance.employee_id.location_id.detect_lunch == True:
				if any(self.get_native_time(x.check_out, employee_tz).time() > time(13,0) and self.get_native_time(x.check_out, employee_tz).time() < time(14,0) for x in attendance.line_ids) and any(self.get_native_time(x.check_in, employee_tz).time() > time(13,0) and self.get_native_time(x.check_in, employee_tz).time() < time(14,0) for x in attendance.line_ids):
					pass
				else:
					data_to_load_html_template.append([
						'Less 1 hour for the lunch break', ' ', ' ', self.float_to_time(-1)
					])
			row_3 = ['Total time excluding break', ' ', ' ' ]
			if attendance.employee_id.location_id.detect_lunch == True:
				if (any(self.get_native_time(x.check_out, employee_tz).time() > time(13,0) and self.get_native_time(x.check_out, employee_tz).time() < time(14,0) for x in attendance.line_ids) and
						any(self.get_native_time(x.check_in, employee_tz).time() > time(13,0) and self.get_native_time(x.check_in, employee_tz).time() < time(14,0) for x in attendance.line_ids)):
					row_3.append(self.float_to_time((attendance.worked_hours)))
				else:
					row_3.append(self.float_to_time((attendance.worked_hours-1)))
			else:
				row_3.append(self.float_to_time((attendance.worked_hours)))
			row_3.append(' ')
			data_to_load_html_template.append(row_3)
			data_to_load_html_template.append([
				'Breaks', ' ', ' ', 'Counted', 'Non-Counted'
			])
			check_out = False;non_count = timedelta(days=0);count = timedelta(days=0)
			row = [' ', ' ', ' ', ' ', ' ', ' ']
			start_time = self.env.company.company_start_time
			# Extract hour and minute from the float
			hours = int(start_time)
			minutes = int((start_time - hours) * 100)
			attendance_checkin = check_in_utc_naive
			# Create a datetime object with the extracted hour and minute
			start_time_date = datetime(sterday.year, sterday.month, sterday.day, hours, minutes)
			start_time_date = self.get_native_time(start_time_date, employee_tz)

			if attendance_checkin > start_time_date:
				row[0] = 'Break (Delay)'
				row[1] = start_time_date.strftime("%d-%m-%Y %H:%M:%S")
				row[2] = attendance_checkin.strftime(
					"%d-%m-%Y %H:%M:%S")
				start_time_difference = attendance_checkin - start_time_date
				total_late_in_minutes = start_time_difference.total_seconds() // 60
				if total_late_in_minutes > 15:
					row[3] = attendance_checkin - start_time_date
					row[5] = 'claim'
				else:
					row[4] = attendance_checkin - start_time_date
				i+= 1

			for line in attendance.line_ids:
				if j!=1:
					row[2] = self.get_native_time(line.check_in, employee_tz).strftime("%d-%m-%Y %H:%M:%S")
					dif = self.get_native_time(line.check_in, employee_tz) - check_out
					hours = int(dif.seconds / 3600)
					minutes = (dif.seconds % 3600) / 60
					if hours == 0 and minutes <= 15:
						row[4] = str(dif)
						non_count += dif
					else:
						row[3] = str(dif)
						count += dif
					data_to_load_html_template.append(row)
				if k!=j:
					row = [' ', ' ', ' ', False, False, 'claim']
					row[0] = 'Break '+str(j)
					row[1] = self.get_native_time(line.check_out, employee_tz).strftime("%d-%m-%Y %H:%M:%S")
					check_out = self.get_native_time(line.check_out, employee_tz)
				i+=1;j+=1
			data_to_load_html_template.append([
				'Total Breaks', ' ', ' ', str(count), ' '
			])
			wk_hr=timedelta(hours=attendance.worked_hours)
			if attendance.employee_id.location_id.detect_lunch == True:
				if any(self.get_native_time(x.check_out, employee_tz).time() > time(13,0) and self.get_native_time(x.check_out, employee_tz).time() < time(14,0) for x in attendance.line_ids) and any(self.get_native_time(x.check_in, employee_tz).time() > time(13,0) and self.get_native_time(x.check_in, employee_tz).time() < time(14,0) for x in attendance.line_ids):
					bk_hr=non_count
				else:
					bk_hr=non_count+timedelta(hours=1)
			else:
				bk_hr=non_count
			data_to_load_html_template.append([
				'Net total time inside the office (' + str(
					self.float_to_time(attendance.worked_hours)) + ' - ' + str(
					non_count) + ')', ' ', ' ', str(wk_hr-bk_hr), ' '
			])
			base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
			context = {
			    'email_to': attendance.employee_id.work_email,
				'email_from':self.env.company.erp_email,
				'sterday':sterday,
				'base_url': f"{base_url}/attendance/claim/form?date={sterday.strftime('%d-%b-%Y')}&employee_id={attendance.employee_id.id}" ,
				'datas': data_to_load_html_template,
				'com_work_hrs':self.env.company.attend_work_hrs
				}
			template = self.env.ref('tg_attendance.email_template_employee_daily_attendance_alert')
			template.with_context(context).send_mail(attendance.id, force_send=True)

class Employee(models.Model):
	_inherit = "hr.employee"

	def float_to_time(self,float_value):
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
				attendance_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','>=',last_date),('fetch_date','<=',start_date)])
				if attendance_ids:
					leave_count = 0
					leave_days = emp.get_unusual_days_emp(emp.resource_calendar_id,last_date,start_date)
					leave_count += list(leave_days.values()).count(False)
					if sum(attendance_ids.mapped('actual_hours')) < (leave_count * self.env.company.attend_work_hrs):
						avg=sum(attendance_ids.mapped('actual_hours'))/leave_count
						context = {
			    			'email_to':emp.work_email,
							'email_from':self.env.company.erp_email,
							'today':start_date,
							'last_week':last_date,
							'com_work_hrs':self.float_to_time(self.env.company.attend_work_hrs),
							'act_work_hrs': self.float_to_time(avg),
						}
						template = self.env.ref('tg_attendance.email_template_employee_weekly_attendance_timesheet_alert')
						template.with_context(context).send_mail(emp.id, force_send=True)
			
	def _employee_monthly_alert_timesheet_attendance(self):	
		today = fields.date.today()
		previous_month = date_utils.subtract(today, months=1)
		last_day = calendar.monthrange(previous_month.year,previous_month.month)[1]
		start_date = previous_month.replace(day=1, month=previous_month.month, year=previous_month.year)
		last_date = previous_month.replace(day=last_day, month=previous_month.month, year=previous_month.year)
		emp_ids = self.env['hr.employee'].search([])
		for emp in emp_ids:
			attendance_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','>=',start_date),('fetch_date','<=',last_date)])
			if attendance_ids:
				leave_count = 0
				leave_days = emp.get_unusual_days_emp(emp.resource_calendar_id,start_date,last_date)
				leave_count += list(leave_days.values()).count(False)
				if sum(attendance_ids.mapped('actual_hours')) < (leave_count * self.env.company.attend_work_hrs):
					avg=sum(attendance_ids.mapped('actual_hours'))/leave_count
					context = {
		    			'email_to':emp.work_email,
						'email_from':self.env.company.erp_email,
						'month':previous_month.strftime("%B"),
						'com_work_hrs':self.env.company.attend_work_hrs,
						'act_work_hrs':self.float_to_time(avg),
					}
					template = self.env.ref('tg_attendance.email_template_employee_monthly_attendance_timesheet_alert')
					template.with_context(context).send_mail(emp.id, force_send=True)
		

class TgAttendanceLine(models.Model):
	_name = "hr.attendance.line"
	_description = "Attendance Timesheet"
	_order = "id asc"

	header_id = fields.Many2one("hr.attendance")
	employee_id = fields.Many2one("hr.employee",'Employee',related='header_id.employee_id',store=True)
	check_in = fields.Datetime("Check In")
	check_out = fields.Datetime("Check Out")
	worked_hours = fields.Float("Logged Hours",compute='_compute_worked_hours',store=True)
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

