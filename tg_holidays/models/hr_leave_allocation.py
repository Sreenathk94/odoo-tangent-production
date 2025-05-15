# models/hr_leave_allocation.py
from odoo import models, fields


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    is_probation_accrual = fields.Boolean("Probation Leave Accrual")
    is_post_probation_allocation = fields.Boolean("Post-Probation Leave Allocation")
    is_annual_allocation = fields.Boolean(string="Annual Leave Allocation")

