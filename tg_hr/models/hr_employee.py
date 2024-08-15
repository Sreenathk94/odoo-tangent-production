from odoo import fields, models


class HREmployee(models.Model):
	_inherit = "hr.employee"

	passport_expire = fields.Date(string="Passport Expire Date",copy=False)
	permit_expire = fields.Date(string="Labour Card Expire",copy=False)
	emergency_mobile = fields.Char(string="Emergency Mobile")


class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"

	passport_expire = fields.Date(string="Passport Expire Date",copy=False)
	permit_expire = fields.Date(string="Labour Card Expire",copy=False)
	emergency_mobile = fields.Char(string="Emergency Mobile")
