from odoo import models, fields
from datetime import datetime

class HRBonusLeave(models.Model):
    _inherit = 'hr.employee'

    def _allocate_bonus_leaves(self):
        print("🚀 Starting bonus leave allocation process...")

        leave_type = self.env['hr.leave.type'].search([('name', '=', 'Bonus Annual Leave')], limit=1)
        print(leave_type, " ← Leave Type Found")

        if not leave_type:
            leave_type = self.env['hr.leave.type'].create({
                'name': 'Bonus Annual Leave',
                'time_type': 'leave',
                'requires_allocation': 'yes',
                'leave_validation_type': 'hr',
                'allocation_validation_type': 'officer',
            })
            print(f"✅ Created new leave type: {leave_type.name}")
        else:
            print(f"ℹ️ Found existing leave type: {leave_type.name}")

        today = fields.Date.today()
        current_year = today.year

        employees = self.search([])
        print(f"👥 Found {len(employees)} employees to process.")

        for employee in employees:
            print(f"\n🔄 Processing employee: {employee.name} (ID: {employee.id})")

            if not employee.create_date:
                print(f"⛔ Employee {employee.name} has no create_date, skipping.")
                continue

            service_days = (today - employee.date_of_join).days
            years = service_days // 365

            print(f"📅 Service: {service_days} days → {years} full years")

            if years < 3:
                print(f"❌ Not eligible (less than 3 years)")
                continue

            # New logic for bonus leave days
            if years >= 5:
                leave_days = 3
            else:
                leave_days = years - 2  # Only for years 3 or 4

            print(f"🎁 Eligible for {leave_days} bonus leave days")

            already_allocated = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('date_from', '>=', datetime(current_year, 1, 1)),
                ('date_to', '<=', datetime(current_year, 12, 31)),
                ('state', 'in', ['validate', 'confirm', 'draft'])
            ])

            if already_allocated:
                print(f"⚠️ Bonus leave already allocated for {employee.name} this year, skipping.")
                continue

            allocation = self.env['hr.leave.allocation'].create({
                'name': f'Annual Bonus Leave - {current_year}',
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': leave_days,
                'date_from': datetime(current_year, 1, 1),
                'date_to': datetime(current_year, 12, 31),
                # stay in draft
            })

            print(f"✅ Draft leave allocation created for {employee.name}: {leave_days} days")

        print("\n✅ Bonus leave allocation process completed.")
