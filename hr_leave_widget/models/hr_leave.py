from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def get_leave_type_selectability(self, employee_id):
        """Return leave types with selectability based on visa expiry."""
        employee = self.env['hr.employee'].browse(employee_id)
        context = {
            'employee_id': employee_id,
            # 'default_date_from':  datetime.now().date().isoformat(),
            # 'default_date_to':  datetime.now().date().isoformat(),
            'request_type': 'leave',
        }
        domain = [
            '|',
            ('requires_allocation', '=', 'no'),
            '&',
            ('has_valid_allocation', '=', True),
            '|',
            ('allows_negative', '=', True),
            '&',
            ('virtual_remaining_leaves', '>', 0),
            ('allows_negative', '=', False),
        ]
        leave_types = self.env['hr.leave.type'].with_context(context).search(domain)
        six_months_from_now = datetime.now().date() + relativedelta(months=6)
        result = []
        for lt in leave_types:
            selectable = True
            if employee.date_of_join and employee.date_of_join <= six_months_from_now and lt.code in ['SL', 'AL']:
                selectable = False
            result.append({
                'id': lt.id,
                'name': lt.display_name,
                'selectable': selectable
            })
        return result
