from odoo import fields,api,models
import xlwt,base64
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class IndividualTimesheet(models.TransientModel):
	_name = "hr.individual.timesheet.report"
	_description = "Individual Timesheet Report"

	report_type = fields.Selection([('employee','Employee Wise'),('project','Project Wise')],string="Report Type",default='employee')
	employee_id = fields.Many2one("hr.employee","Employee")
	project_id = fields.Many2one('project.project','Project')
	from_date = fields.Date("From Date")
	to_date = fields.Date("To Date")
	file_name = fields.Binary('Report', readonly=True)
	report = fields.Char('Name')

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int(round((float_value - hours) * 60))
		return f"{hours:02d}:{minutes:02d}"

	def generate_excel(self):
		workbook = xlwt.Workbook()
		date_format = xlwt.XFStyle()
		date_format.num_format_str = 'D/MMM/YYYY'
		borders = xlwt.Borders()
		borders.left = 1
		borders.right = 1
		borders.top = 1
		borders.bottom = 1
		date_format.borders = borders
		style0 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom dotted, right thin,left thin;align: horiz center;', num_format_str='#,###,##0.00')
		style1 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom double, right thin,left thin;align: horiz center, wrap 1', num_format_str='DD/MMM/YYYY')
		style2 = xlwt.easyxf('font:height 400,bold True,colour black; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='#,###,##0.00')         
		style3 = xlwt.easyxf('font:height 400,bold True,colour black; borders: top thin,bottom thin, right thin,left thin;align: horiz center;', num_format_str='DD/MMM/YYYY')
		style4 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='DD/MMM/YYYY')
		style5 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		style6 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz left;', num_format_str='#,###,##0')
		style7 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz center;', num_format_str='_(###0.00_);[Red](###0.00)')
		style9 = xlwt.easyxf('font: name Times New Roman; borders: top thin,bottom thin, right thin,left thin;align: horiz center;')
		style8 = xlwt.easyxf('font: name Times New Roman,bold True, colour black;borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		style10 = xlwt.easyxf('font: name Times New Roman,bold True, colour white;borders: top thin,bottom thin, right thin,left thin;align: horiz right;', num_format_str='_(#,##0.00_);[Red](#,##0.00)')
		pattern = xlwt.Pattern()
		pattern.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern.pattern_fore_colour = 0x34
		style1.pattern = pattern
		pattern1 = xlwt.Pattern()
		pattern1.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern1.pattern_fore_colour = xlwt.Style.colour_map['pale_blue']
		style8.pattern = pattern1
		pattern2 = xlwt.Pattern()
		pattern2.pattern = xlwt.Pattern.SOLID_PATTERN
		pattern2.pattern_fore_colour = xlwt.Style.colour_map['black']
		style10.pattern = pattern2
		# style = xlwt.XFStyle()
		style1.alignment.wrap = 1
		day_diff = (self.to_date-self.from_date).days+1
		date_list = []
		current_date = self.from_date
		while current_date <= self.to_date:
			date_list.append(current_date.strftime("%d/%m/%Y"))
			current_date += timedelta(days=1)
		if self.report_type == 'employee':
			employee_ids = self.env['hr.employee'].search([])
			if not employee_ids:
				raise UserError("Warning!! No employees found.")

			sheet = workbook.add_sheet('All Employees - Timesheet Report')
			sheet.row(0).height = 500
			sheet.write_merge(0, 0, 0, day_diff + 3, 'EMPLOYEE TIMESHEET REPORT', style0)

			# Report Header
			sheet.write(1, 0, "From Date", style1)
			sheet.write(1, 1, self.from_date.strftime("%d/%m/%Y"), style4)
			sheet.write(2, 0, "To Date", style1)
			sheet.write(2, 1, self.to_date.strftime("%d/%m/%Y"), style4)

			# Table Header
			sheet.write(4, 0, "S.No", style1)
			sheet.write(4, 1, "Employee Name", style1)
			col_index = 2
			for date in date_list:
				sheet.write(4, col_index, date, style1)
				col_index += 1
			sheet.write(4, col_index, "Total", style1)

			# Populate Employee Data
			row_index = 5
			daily_totals = [0] * day_diff  # To track totals for each day across all employees
			overall_total = 0  # To track total hours for all employees

			for idx, employee in enumerate(employee_ids, start=1):
				sheet.write(row_index, 0, idx, style9)  # S.No
				sheet.write(row_index, 1, employee.name, style4)  # Employee Name

				startdate = self.from_date
				employee_total = 0
				col_index = 2

				for day in range(day_diff):
					timesheet_ids = self.env['account.analytic.line'].search([
						('employee_id', '=', employee.id),
						('date', '=', startdate),
					])
					daily_hours = sum([x.unit_amount for x in timesheet_ids])
					employee_total += daily_hours
					daily_totals[day] += daily_hours

					# Daily Hours
					sheet.write(row_index, col_index, self.float_to_time(daily_hours), style7)
					startdate += timedelta(days=1)
					col_index += 1

				# Employee Total
				sheet.write(row_index, col_index, self.float_to_time(employee_total), style8)
				overall_total += employee_total
				row_index += 1

			# Total Row (Footer)
			sheet.write(row_index, 0, "", style1)  # Leave S.No blank
			sheet.write(row_index, 1, "Total", style1)  # Label
			col_index = 2
			for total in daily_totals:
				sheet.write(row_index, col_index, self.float_to_time(total), style8)
				col_index += 1
			sheet.write(row_index, col_index, self.float_to_time(overall_total), style10)

			# Save Filename for Employee Wise Report
			filename = 'Employee_Wise_Timesheet_Report_%s_to_%s.xls' % (
				self.from_date.strftime("%d-%m-%Y"),
				self.to_date.strftime("%d-%m-%Y")
			)
		else:
			timesheet = employee_ids = []
			sheet = workbook.add_sheet('%s - Timesheet Report'%(self.project_id.name))
			timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
				('date','>=',self.from_date),('date','<=',self.to_date)])
			if timesheet_ids:
				employee_ids = timesheet_ids.mapped('employee_id')
			else:
				raise UserError("Warning!!, No record found!")

			sheet.row(0).height = 500
			sheet.write_merge(0, 0, 0, 9, 'PROJECT TIMESHEET REPORT',style2)
			sheet.write(1,0,"No",style1)
			sheet.write(1,1,self.project_id.project_number,style4)
			sheet.write(1,2,"Name",style1)
			sheet.write(1,3,self.project_id.name,style4)
			sheet.write(2,0,"From Date",style1)
			sheet.write(2,1,self.from_date,style4)
			sheet.write(3,0,"To Date",style1)
			sheet.write(3,1,self.to_date,style4)
			
			sheet.write(5,0,"S.No",style1)
			sheet.write(5,1,"Employee",style1)
			n = 2
			for day in date_list:
				sheet.write(5,n,day,style1)
				n += 1
			sheet.write(5,n,'Total',style1)
			i = 1; m = 6
			for rec in employee_ids:
				sheet.write(m, 0, i, style9)
				sheet.write(m, 1, rec.name, style4)
				startdate = self.from_date
				j=1;h=2;p_tot = 0
				while j <= day_diff:
					timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
						('date','>=',startdate),('date','<=',startdate),('employee_id','=',rec.id)])
					sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style7)
					startdate = startdate + timedelta(days=1)
					p_tot += sum([x.unit_amount for x in timesheet_ids])
					j += 1
					h += 1
				sheet.write(m, h, self.float_to_time(p_tot), style8)
				i += 1
				m += 1
			sheet.write_merge(m,m,0,1,"Total",style1)
			j = 1;h=2
			startdate = self.from_date
			while j <= day_diff:
				timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
					('date','>=',startdate),('date','<=',startdate)])
				sheet.write(m, h, self.float_to_time(sum([x.unit_amount for x in timesheet_ids])), style8)
				startdate = startdate + timedelta(days=1)
				j+=1
				h+=1
			timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',self.project_id.id),
					('date','>=',self.from_date),('date','<=',self.to_date)])
			sheet.write(m,h,self.float_to_time(sum([x.unit_amount for x in timesheet_ids])),style10)
			filename = ('%s-%s Timesheet Report (%s - %s)'%(self.project_id.project_number,self.project_id.name,self.from_date.strftime("%d-%m-%Y"),self.to_date.strftime("%d-%m-%Y"))+'.xls')
		filename_tmp = '/tmp/' + filename
		workbook.save(filename_tmp)
		fp = open(filename_tmp, "rb")
		file_data = fp.read()
		out = base64.b64encode(file_data)
		self.write({'report':filename, 'file_name':out})
		fp.close()
		
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'hr.individual.timesheet.report',
			'res_id': self.id,
			'view_type': 'form',
			'view_mode': 'form',
			'context': self.env.context,
			'target': 'new',
		}