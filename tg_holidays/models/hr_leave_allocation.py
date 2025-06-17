# models/hr_leave_allocation.py
from odoo import api, models, fields
from odoo.tools import float_round



class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    is_probation_accrual = fields.Boolean("Probation Leave Accrual")
    is_post_probation_allocation = fields.Boolean("Post-Probation Leave Allocation")
    is_annual_allocation = fields.Boolean(string="Annual Leave Allocation")
    is_carry_forward = fields.Boolean(string="Carry Forward Annual Leave Allocation")
    leave_mode = fields.Selection([
        ('paid', 'Paid Leave'),
        ('compensatory', 'Compensatory Days'),
    ], string="Leave Mode", default='compensatory')
    state = fields.Selection(selection_add=[('paid', 'Paid Leave Confirmed')])
    is_cp_leave = fields.Boolean("Is Compensatory Allocation", default=False)
    duration_days_only = fields.Float(
        string='Requested (Days Only)',
        compute='_compute_duration_days_only',
        help="Displays the duration of the leave request strictly in days."
    )

    @api.depends('number_of_days_display', 'number_of_hours_display', 'type_request_unit')
    def _compute_duration_days_only(self):
        for record in self:
            if record.type_request_unit == 'hour':

                record.duration_days_only = float_round(record.number_of_hours_display / 9.0,
                                                        precision_digits=2)  # assuming 9 hours = 1 day
            else:
                record.duration_days_only = float_round(record.number_of_days_display, precision_digits=2)

    @api.onchange('holiday_status_id')
    def compute_is_cp_leave(self):
        for rec in self:
            rec.is_cp_leave = rec.holiday_status_id.code == 'CP'

    def action_validate(self):
        for record in self:
            if record.holiday_status_id.code == 'CP':
                if record.leave_mode == 'paid':
                    # Custom state transition or logic for paid leave
                    record.write({'state': 'paid'})
                    return  # skip normal process
        return super().action_validate()

    def action_refuse(self):
        for record in self:
            if record.state == 'paid':
                record.write({'state': 'refuse'})
                return
        return super().action_refuse()

