from odoo import fields, api, models
from datetime import datetime,date,time
from dateutil.relativedelta import relativedelta
import pytz
from dateutil.rrule import rrule, DAILY


class HREmployee(models.Model):
	_inherit = "hr.employee"
	
	not_required = fields.Boolean('Timesheet Not Required')
	date_of_join = fields.Date("Date of Joining", required=True)
	
	@api.model_create_multi
	def create(self, vals):
		lines = super(HREmployee, self).create(vals)
		if vals.get('not_required') == False:
			submit_ids = self.env['hr.timesheet.submit'].search([('to_date','>=',date.today())])
			for submit_id in submit_ids:
				for line in lines:
					self.env['hr.timesheet.submit.line'].sudo().create({'employee_id':line.id,'submit_id':submit_id.id})
		return lines
	
	def write(self, vals):
		res = super(HREmployee, self).write(vals)
		if vals.get('not_required')==False:
			submit_ids = self.env['hr.timesheet.submit'].search([('to_date','>=',date.today())])
			for submit_id in submit_ids:
				if not self.env['hr.timesheet.submit.line'].search([('employee_id','=',self.id),('submit_id','=',submit_id.id)]):
					self.env['hr.timesheet.submit.line'].sudo().create({'employee_id':self.id,'submit_id':submit_id.id})
		return res

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int((float_value - hours) * 60)
		return f"{hours:02d}:{minutes:02d}"

	def _entry_employee_timesheet_daily_alert(self):
		employee_ids = self.env["hr.employee"].search([('active','=',True),('not_required','=',False)])
		sterday = datetime.now().date() - relativedelta(days=1)
		for emp in employee_ids:
			leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,sterday,sterday)
			leave_id = self.env['hr.leave'].search([('request_date_from','<=',sterday),('request_date_to','>=',sterday),('employee_id','=',emp.id),('state','=','validate')])
			if leave_day[sterday.strftime("%Y-%m-%d")] == False and not leave_id:
				timesheet_ids = self.env['account.analytic.line'].search([('date','>=',sterday),('date','<=',sterday),
					('employee_id','=',emp.id)])
				if not timesheet_ids:
					context = {
						'email_to': emp.work_email,
						'subject': "Fouvty - System Notification: Timesheet Update Required for %s" % (
							sterday.strftime("%d/%m/%Y")),
					}
					template_id = self.env.ref(
						'sttl_timesheet_calendar.email_template_daily_timesheet_alert')
					if template_id:
						template_id.with_context(
							sterday=sterday.strftime("%d/%m/%Y")).send_mail(
							emp.id,
							force_send=True,
							email_values=context)

	@api.model
	def get_unusual_days_emp(self, calendar_id, date_from, date_to=None):
		calendar = calendar_id
		if not calendar:
			return {}
		tz = pytz.timezone('UTC')
		dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
		dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)
		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}


class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"
	
	not_required = fields.Boolean('Timesheet Not Required')
	date_of_join = fields.Date("Date of Joining")
	
