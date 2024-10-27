from odoo import models, api, fields
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    """Inherited model for hr.leave with additional methods"""
    _inherit = 'hr.leave'

    @api.constrains('holiday_status_id', 'request_date_from', 'request_date_to',
                    'supported_attachment_ids')
    def check_leave_status(self):
        """
        Checks if the leave status is valid.
        Valid leave statuses are 'sick'.
        """
        if self.holiday_status_id.id == self.env.ref(
                'hr_holidays.holiday_status_sl').id:
            if self.number_of_days_display and self.number_of_days_display >= 2 and not self.supported_attachment_ids:
                raise ValidationError(
                    "Employees must submit an attachment or a medical report for any sick leave lasting two or more consecutive days.")

            if self.number_of_days_display and self.number_of_days_display == 1 and not self.supported_attachment_ids:
                request_date_from = self.request_date_from
                date_obj = fields.Date.from_string(self.request_date_from)
                # Check if the day is Monday (0) or Friday (4)
                if date_obj.weekday() in (0, 4):
                    day = "Monday" if date_obj.weekday() == 0 else "Friday"
                    raise ValidationError(
                        f"Employee must submit an attachment or medical report if the leave starts on {day}"
                    )

    @api.depends('leave_type_support_document', 'attachment_ids')
    def _compute_supported_attachment_ids(self):
        for holiday in self:
            holiday.supported_attachment_ids = holiday.attachment_ids
            holiday.supported_attachment_ids_count = len(holiday.attachment_ids.ids)
