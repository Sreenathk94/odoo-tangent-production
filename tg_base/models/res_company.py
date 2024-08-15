from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    erp_email = fields.Char(string="ERP Email")
    company_seal = fields.Binary(string="Company Seal")
    ## timesheet
    timesheet_working_hrs = fields.Float(string="Working Hours(HH:MM)", default=9)
    timesheet_manager_alert = fields.Integer(string="No of days interval for sending email notification to manager",
                                             default=15)
    timesheet_manager_nxt_date = fields.Date(string="Next Date")
    timesheet_admin_alert = fields.Integer(string="No of days interval for sending email notification to admin", default=30)
    timesheet_admin_nxt_date = fields.Date(string="Next Date")
    ## leave
    absent_manager_alert = fields.Integer(string="No of days interval for sending email notification to manager", default=15)
    absent_manager_nxt_date = fields.Date(string="Next Date")
    # attendance
    attend_work_hrs = fields.Float(string="Login Hours(HH:MM)", default=9)
    company_start_time = fields.Float(string="Company Start Time(HH:MM)", default=9)

    @api.onchange("timesheet_manager_alert")
    def update_timesheet_manager_nxt_date(self):
        if self.timesheet_manager_alert > 0:
            self.timesheet_manager_nxt_date = datetime.now().date() + relativedelta(days=self.timesheet_manager_alert)
        else:
            self.timesheet_manager_nxt_date = datetime.now().date()

    @api.onchange("timesheet_admin_alert")
    def update_timesheet_admin_nxt_date(self):
        if self.timesheet_admin_alert > 0:
            self.timesheet_admin_nxt_date = datetime.now().date() + relativedelta(days=self.timesheet_admin_alert)
        else:
            self.timesheet_admin_nxt_date = datetime.now().date()

    @api.onchange("absent_manager_alert")
    def update_leave_manager_nxt_date(self):
        if self.absent_manager_alert > 0:
            self.absent_manager_nxt_date = datetime.now().date() + relativedelta(days=self.absent_manager_alert)
        else:
            self.absent_manager_nxt_date = datetime.now().date()
