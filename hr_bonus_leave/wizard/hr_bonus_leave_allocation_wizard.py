from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrBonusLeaveAllocationWizard(models.TransientModel):
    _name = 'hr.bonus.leave.allocation.wizard'
    _description = 'Bonus Leave Allocation Wizard'
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True
    )
    
    allocation_year = fields.Char(
        string='Allocation Year',
        required=True,
        default=lambda self: str(fields.Date.today().year)
    )
    
    def action_allocate_bonus_leave(self):
        """Manually allocate bonus leave to selected employees"""
        self.ensure_one()
        
        # Get the bonus leave type
        leave_type = self.env.ref('hr_bonus_leave.leave_type_bonus', raise_if_not_found=False)
        if not leave_type:
            raise UserError(_('Bonus leave type not found. Please check your configuration.'))
        
        # Check for existing allocations
        allocated_employees = self.env['hr.bonus.leave.allocation.log'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('allocation_year', '=', self.allocation_year)
        ]).mapped('employee_id')
        
        if allocated_employees:
            skipped_names = ', '.join(allocated_employees.mapped('name'))
            raise UserError(_(
                'The following employees already received bonus leave for year %s: %s',
                self.allocation_year, skipped_names
            ))
        
        # Allocate leave for eligible employees
        allocation_count = 0
        for employee in self.employee_ids:
            bonus_days = employee.get_bonus_leave_days()
            if bonus_days <= 0:
                continue
                
            # Create allocation
            allocation = self.env['hr.leave.allocation'].create({
                'name': _('Annual Bonus Leave - %s', self.allocation_year),
                'holiday_status_id': leave_type.id,
                'employee_id': employee.id,
                'number_of_days': bonus_days,
                'allocation_type': 'regular',
                'state': 'validate',
                'is_bonus_leave': True,
            })
            
            # Log the allocation
            self.env['hr.bonus.leave.allocation.log'].create({
                'employee_id': employee.id,
                'allocation_id': allocation.id,
                'years_of_service': employee.years_of_service,
                'days_allocated': bonus_days,
                'allocation_year': self.allocation_year
            })
            
            allocation_count += 1
        
        # Show success message
        if allocation_count:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bonus Leave Allocation'),
                    'message': _('Bonus leave allocated to %s employees.', allocation_count),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Bonus Leave Allocation'),
                    'message': _('No eligible employees found for bonus leave allocation.'),
                    'sticky': False,
                    'type': 'warning',
                }
            } 