# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta, datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_round

_logger = logging.getLogger(__name__)


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    allocation_type = fields.Selection(
        selection_add=[
            ('annual', 'Annual Leave'),
            ('carry_forward', 'Carry Forward Leave'),
            ('bonus', 'Bonus Leave'),
            ('sick', 'Sick Leave'),
        ],
        ondelete={
            'annual': 'cascade',
            'carry_forward': 'cascade',
            'bonus': 'cascade',
            'sick': 'cascade',
        }
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    leave_exemption = fields.Boolean(
        string="Leave Exemption",
        help="If enabled, full remaining annual leave is carried forward (no limit)"
    )

    leave_exemption_line_ids = fields.One2many(
        'hr.leave.exemption.line',
        'employee_id',
        string="Leave Exemption Limits"
    )
    def _get_remaining_leave(self, leave_type, year):
        self.ensure_one()

        date_from = date(year, 1, 1)
        date_to = date(year, 12, 31)

        Allocation = self.env['hr.leave.allocation']
        Leave = self.env['hr.leave']

        hours_per_day = self.resource_calendar_id.hours_per_day or 9.0

        # --------------------------------------------------
        # 1️⃣ ALLOCATED DAYS (allocation has ONLY days)
        # --------------------------------------------------
        alloc_data = Allocation._read_group(
            [
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ],
            aggregates=['number_of_days:sum'],
            groupby=[]
        )

        allocated_days = alloc_data[0][0] if alloc_data and alloc_data[
            0] else 0.0

        # --------------------------------------------------
        # 2️⃣ TAKEN HOURS (leave has reliable hours)
        # --------------------------------------------------
        leave_data = Leave._read_group(
            [
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', date_to),
                ('request_date_to', '>=', date_from),
            ],
            aggregates=['number_of_hours:sum'],
            groupby=[]
        )

        taken_hours = leave_data[0][0] if leave_data and leave_data[0] else 0.0
        taken_days = taken_hours / hours_per_day

        remaining_days = allocated_days - taken_days

        _logger.info(
            """
            🧮 LEAVE BALANCE (FINAL – CORRECT)
            Employee : %s
            Leave    : %s
            Year     : %s
            Alloc D  : %s
            Taken H  : %s
            Taken D  : %s
            Remain D : %s
            """,
            self.name,
            leave_type.name,
            year,
            allocated_days,
            taken_hours,
            taken_days,
            remaining_days
        )

        return float_round(remaining_days, precision_digits=2)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    medical_document = fields.Binary(
        string="Medical Certificate",
        help="Upload medical certificate for sick leave"
    )
    medical_document_filename = fields.Char(string="Filename")
    medical_doc_verified = fields.Boolean(
        string="Document Verified by HR",
        groups="hr.group_hr_manager",
        help="HR verification of medical certificate"
    )
    approval_level = fields.Integer(
        string="Current Approval Level",
        default=0,
        tracking=True
    )
    approval_description = fields.Char(
        string="Current Approval Level",
        default=0,
        tracking=True
    )

    approval_flow_id = fields.Many2one(
        'hr.leave.approval.flow',
        string="Current Approval Step"
    )

    approval_done = fields.Boolean(
        string="Approval Completed",
        default=False
    )
    can_current_user_approve = fields.Boolean(
        string="Can Approve (UI)",store=True,
        default=True
    )

    is_sick_leave = fields.Boolean(string="Is Sick Leave", store=True,
        help="Mark this leave type as sick leave for document validation"
    )

    @api.onchange('approval_flow_id', 'approval_flow_id.group_ids', 'state',
                  'approval_done', 'holiday_status_id')
    def _onchange_can_current_user_approve(self):
        """Compute if current user can approve the leave."""
        user = self.env.user
        user_groups = user.groups_id
        for leave in self:
            # Set sick leave flag
            leave.is_sick_leave = leave.holiday_status_id.is_sick_leave

            # Non-custom validation: cannot approve
            if leave.holiday_status_id.leave_validation_type != 'custom':
                print('kkkkkkkkkkkkkkkkkk', leave.holiday_status_id.leave_validation_type)
                leave.can_current_user_approve = False
            else:
                leave.can_current_user_approve = True

                continue

            # Custom validation logic
            if leave.state != 'confirm':
                leave.can_current_user_approve = False
                continue

            if leave.approval_done:
                leave.can_current_user_approve = False
                continue

            if not leave.approval_flow_id:
                leave.can_current_user_approve = False
                continue

            # Check if user belongs to the approval groups
            if leave.approval_flow_id.group_ids & user_groups:
                leave.can_current_user_approve = True
            else:
                leave.can_current_user_approve = False


    @api.constrains('holiday_status_id', 'request_date_from', 'request_date_to')
    def _check_sick_leave_document(self):
        """Validate sick leave document requirements"""
        for leave in self:
            if not leave.holiday_status_id.is_sick_leave:
                continue

            # Only check for Dubai employees
            if not leave.employee_id.work_location_id or leave.employee_id.work_location_id.name != 'Dubai':
                continue

            require_doc = False
            reason = []

            # 1. Count sick leaves in current year (more than 7)
            year_start = date(leave.request_date_from.year, 1, 1)
            year_end = date(leave.request_date_from.year, 12, 31)

            sick_count = self.search_count([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('state', '=', 'validate'),
                ('request_date_from', '>=', year_start),
                ('request_date_to', '<=', year_end),
                ('id', '!=', leave.id),
            ])

            if sick_count >= 7:
                require_doc = True
                reason.append("You have already taken 7 or more sick leaves this year")

            # 2. Sandwich leave (Friday AND Monday) - Fixed logic
            if self._is_sandwich_leave(leave.request_date_from, leave.request_date_to):
                require_doc = True
                reason.append("Sandwich leave detected (Friday-Monday)")

            # 3. Overlaps with public holiday
            public_holidays = self.env['resource.calendar.leaves'].search([
                ('calendar_id', '=', False),
                '|',
                '&',
                ('date_from', '<=', leave.request_date_from),
                ('date_to', '>=', leave.request_date_from),
                '&',
                ('date_from', '<=', leave.request_date_to),
                ('date_to', '>=', leave.request_date_to),
            ])

            if public_holidays:
                require_doc = True
                reason.append("Leave overlaps with a public holiday")

            # Adjacent to public holiday
            day_before = leave.request_date_from - timedelta(days=1)
            day_after = leave.request_date_to + timedelta(days=1)

            adjacent_holidays = self.env['resource.calendar.leaves'].search([
                ('calendar_id', '=', False),
                '|',
                '&',
                ('date_from', '<=', day_before),
                ('date_to', '>=', day_before),
                '&',
                ('date_from', '<=', day_after),
                ('date_to', '>=', day_after),
            ])

            if adjacent_holidays:
                require_doc = True
                reason.append("Leave is immediately before/after a public holiday")

            # 4. Adjacent to annual leave
            day_before = leave.request_date_from - timedelta(days=1)
            day_after = leave.request_date_to + timedelta(days=1)

            adjacent_annual = self.search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id.annual_leave_boolean', '=', True),
                ('state', '=', 'validate'),
                ('id', '!=', leave.id),
                '|',
                '&',
                ('request_date_from', '<=', day_before),
                ('request_date_to', '>=', day_before),
                '&',
                ('request_date_from', '<=', day_after),
                ('request_date_to', '>=', day_after),
            ])

            if adjacent_annual:
                require_doc = True
                reason.append("Leave is immediately before/after annual leave")

            if require_doc and not leave.medical_document:
                reason_text = "\n".join(f"- {r}" for r in reason)
                raise ValidationError(
                    f"Medical certificate is mandatory for this sick leave.\n\n"
                    f"Reasons:\n{reason_text}\n\n"
                    f"Please upload a medical certificate to proceed."
                )

    def _is_sandwich_leave(self, from_date, to_date):
        """Check if the leave period includes both a Friday and the following Monday"""
        current = from_date
        while current <= to_date:
            if current.weekday() == 4:  # Friday
                monday = current + timedelta(days=3)
                if monday <= to_date:
                    return True
            current += timedelta(days=1)
        return False

    def action_confirm(self):
        res = super().action_confirm()

        for leave in self:
            if leave.holiday_status_id.leave_validation_type != 'custom':
                continue

            flow_lines = leave.holiday_status_id.approval_flow_line_ids.sorted(
                'sequence')
            if not flow_lines:
                raise ValidationError(
                    _("Approval flow is not configured for this leave type.")
                )

            first_flow = flow_lines[0]
            leave.approval_description = ('Level ' + str(first_flow.sequence) +
                                    'Approved by' + self.env.user.name)
            leave.approval_level = first_flow.sequence
            leave.approval_flow_id = first_flow.id

        return res

    # def action_confirm(self):
    #     res = super().action_confirm()
    #
    #     for leave in self:
    #         if leave.holiday_status_id.leave_validation_type != 'custom':
    #             continue
    #
    #         flows = leave.holiday_status_id.approval_flow_line_ids.sorted(
    #             'sequence')
    #         if not flows:
    #             raise ValidationError(_("Approval flow not configured."))
    #
    #         leave.approval_level = flows[0].sequence
    #         leave.approval_flow_id = flows[0].id
    #         leave.state = 'confirm'
    #
    #     return res

    def _user_can_approve(self):
        self.ensure_one()
        return bool(
            self.approval_flow_id
            and self.approval_flow_id.group_ids & self.env.user.groups_id
        )

    def action_custom_approve(self):
        for leave in self:
            if not self.can_current_user_approve:
                raise UserError(
                    _("You are not authorized to approve this leave."))

            current_flow = leave.approval_flow_id
            flows = leave.holiday_status_id.approval_flow_line_ids.sorted(
                'sequence')

            # ------------------------------------------------
            # FINAL LEVEL → ONLY MARK APPROVAL DONE
            # ------------------------------------------------
            if current_flow.is_final:
                leave.approval_done = True

                leave.message_post(
                    body=_(
                        "Final approval completed by %s"
                    ) % self.env.user.name
                )
                leave.can_current_user_approve = False

                return True  # ⛔ DO NOT VALIDATE HERE

            # ------------------------------------------------
            # MOVE TO NEXT LEVEL
            # ------------------------------------------------
            next_flow = flows.filtered(
                lambda f: f.sequence > current_flow.sequence
            )[:1]

            if leave.holiday_status_id.leave_validation_type == 'custom'\
                    and not next_flow:
                raise ValidationError(_("Approval flow configuration error."))

            leave.approval_flow_id = next_flow.id
            leave.approval_level = next_flow.sequence

            leave.message_post(
                body=_(
                    "Level %s approved by %s"
                ) % (current_flow.sequence, self.env.user.name)
            )


    def action_approve(self):
        for leave in self:
            if (
                leave.employee_id.work_location_id
                and leave.employee_id.work_location_id.name == 'Dubai'
                and leave.holiday_status_id.is_sick_leave
                and (not leave.medical_document or not leave.medical_doc_verified)
            ):
                raise ValidationError(
                    "HR/Manager must verify the medical document before approving the sick leave."
                )
        return super().action_approve()

    def action_validate(self):
        for leave in self:
            if (
                    leave.holiday_status_id.leave_validation_type == 'custom'
                    and not leave.approval_done
            ):
                raise UserError(
                    _("Complete all approval levels before final validation.")
                )

        for leave in self:
            if (
                leave.employee_id.work_location_id
                and leave.employee_id.work_location_id.name == 'Dubai'
                and leave.holiday_status_id.is_sick_leave
                and leave.medical_document
                and not leave.medical_doc_verified
            ):
                raise ValidationError(
                    "HR/Manager must verify the medical document before approval"
                )
        for leave in self.filtered(
                lambda l: l.state == 'validate' and l.employee_id.user_id):
            user = leave.employee_id.user_id
            partner = user.partner_id

            leave.message_post(
                body=_(
                    "✅ <b>Your time off request has been approved</b><br/>"
                    "<ul>"
                    "<li><b>Type:</b> %s</li>"
                    "<li><b>From:</b> %s</li>"
                    "<li><b>To:</b> %s</li>"
                    "<li><b>Duration:</b> %.2f %s</li>"
                    "</ul>",
                    leave.holiday_status_id.display_name,
                    leave.request_date_from,
                    leave.request_date_to,
                    leave.number_of_hours_display if leave.leave_type_request_unit == 'hour' else leave.number_of_days,
                    _("hours") if leave.leave_type_request_unit == 'hour' else _(
                        "days"),
                ),
                partner_ids=[partner.id],
                subtype_xmlid="mail.mt_comment",
            )
        return super().action_validate()


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    carry_forward_max = fields.Integer(
        string="Max Carry Forward (Days)",
        default=7,  # As per updated requirement
        help="Maximum days that can be carried forward to next year"
    )
    annual_leave_boolean = fields.Boolean(
        string="Is Annual Leave",
        help="Mark this leave type as annual leave for carry forward"
    )
    is_sick_leave = fields.Boolean(
        string="Is Sick Leave",store=True,
        help="Mark this leave type as sick leave for document validation"
    )
    leave_validation_type = fields.Selection(
        selection_add=[
            ('custom', 'Custom Approval Flow'),
        ],
        ondelete={'custom': 'set default'}
    )

    approval_flow_line_ids = fields.One2many(
        'hr.leave.approval.flow',
        'leave_type_id',
        string="Approval Flow"
    )

    @api.model
    def run_yearly_leave_allocation(self, target_year=None):
        # leaves = self.env['hr.leave'].search([
        #     ('state', '=', 'validate'),
        #     '|',
        #     ('number_of_days', '=', 0),
        #     ('number_of_days', '=', False),
        # ])
        #
        # for leave in leaves:
        #     # # Core Odoo recomputation
        #     # leave._compute_duration()
        #     #
        #     # _logger.info(
        #     #     "Repaired leave %s | %s | Hours=%s | Days=%s",
        #     #     leave.id,
        #     #     leave.employee_id.name,
        #     #     leave.duration_display,
        #     #     leave.number_of_days
        #     # )

        """Cron method to allocate leaves for the next year. Can be run manually or via cron."""
        today = fields.Date.today()
        if not target_year:
            target_year = today.year + 1 if today.month == 12 and today.day == 31 else today.year
        prev_year = target_year - 1

        _logger.info("🔁 Starting yearly leave allocation for target year: %s (from prev year: %s)", target_year, prev_year)
        print(f"Starting yearly leave allocation for {target_year}")

        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('work_location_id.name', '=', 'Dubai'),
        ])

        if not employees:
            _logger.warning("⚠ No active Dubai employees found for allocation")
            print("No Dubai employees found")
            return

        # Get or create the single annual and sick types for target year
        annual_type = self._get_or_create_annual_leave_type(target_year)
        sick_type = self._get_or_create_sick_leave_type(target_year)

        for emp in employees:
            _logger.info("Processing employee: %s", emp.name)
            print(f"Processing {emp.name}")

            if self._has_allocations(emp, target_year):
                _logger.warning("⏭ Skipping %s – allocations already exist for %s", emp.name, target_year)
                print(f"Skipping {emp.name} - allocations exist for {target_year}")
                continue

            # 1. Sick Leave allocation (separate type)
            self._create_allocation(emp, sick_type, 15, target_year, 'Sick Leave Allocation', 'sick')

            # 2. Annual Leave allocations (all under same annual type)
            # Regular annual: 22 days
            self._create_allocation(emp, annual_type, 22, target_year, 'Annual Leave Allocation', 'annual')

            # Carry forward from prev year
            carry_days = self._compute_carry_forward(emp, prev_year, annual_type)
            if carry_days > 0:
                self._create_allocation(emp, annual_type, carry_days, target_year, 'Carry Forward Leave Allocation', 'carry_forward')

            # Bonus based on years
            bonus_days = self._compute_bonus_leave(emp)
            if bonus_days > 0:
                self._create_allocation(emp, annual_type, bonus_days, target_year, 'Bonus Leave Allocation', 'bonus')

        _logger.info("✅ Yearly leave allocation completed for %s", target_year)
        print(f"Completed allocation for {target_year}")

    def _get_or_create_annual_leave_type(self, year):
        name = f"Annual Leave {year}"
        leave_type = self.search([('name', '=', name)], limit=1)
        if leave_type:
            _logger.info("Using existing Annual Leave type: %s", name)
            return leave_type

        leave_type = self.create({
            'name': name,
            'code': f'AL{year}',
            'active': True,
            'requires_allocation': 'yes',
            'request_unit': 'day',
            'leave_validation_type': 'both',
            'allocation_validation_type': 'officer',
            'carry_forward_max': 7,
            'annual_leave_boolean': True,
            'time_type': 'leave',
            'color': 8,
        })
        _logger.info("🆕 Created Annual Leave type: %s", name)
        print(f"Created {name}")
        return leave_type

    def _get_or_create_sick_leave_type(self, year):
        name = f"Sick Leave {year}"
        leave_type = self.search([('name', '=', name)], limit=1)
        if leave_type:
            _logger.info("Using existing Sick Leave type: %s", name)
            return leave_type

        leave_type = self.create({
            'name': name,
            'code': f'SL{year}',
            'active': True,
            'requires_allocation': 'yes',
            'request_unit': 'day',
            'leave_validation_type': 'both',
            'allocation_validation_type': 'officer',
            'carry_forward_max': 0,
            'is_sick_leave': True,
            'time_type': 'leave',
            'color': 5,
        })
        _logger.info("🆕 Created Sick Leave type: %s", name)
        print(f"Created {name}")
        return leave_type

    def _has_allocations(self, employee, year):
        count = self.env['hr.leave.allocation'].search_count([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date(year, 1, 1)),
            ('date_to', '<=', date(year, 12, 31)),
            ('state', '!=', 'cancel')
        ])
        if count > 0:
            print(f"Allocations exist for {employee.name} in {year}: {count}")
        return count > 0

    def _compute_carry_forward(self, employee, prev_year, annual_type):
        prev_annual_type = self.search([
            ('code', 'ilike', str(prev_year)),
            ('annual_leave_boolean', '=', True),
        ], limit=1)

        if not prev_annual_type:
            return 0

        remaining_days = employee._get_remaining_leave(prev_annual_type,
                                                       prev_year)

        if remaining_days <= 0:
            return 0

        # ----------------------------------------
        # 🟢 LEAVE EXEMPTION LOGIC
        # ----------------------------------------
        if employee.leave_exemption:
            exemption_line = employee.leave_exemption_line_ids.filtered(
                lambda l: l.year == prev_year
            )

            if exemption_line:
                limit = exemption_line.exemption_limit
                carry_days = min(remaining_days, limit)

                _logger.info(
                    "📦 Exemption Carry | %s | Remaining=%s | Limit=%s | Carry=%s",
                    employee.name,
                    remaining_days,
                    limit,
                    carry_days
                )
                return carry_days

            # If exemption enabled but no row → fallback to normal rule
            _logger.warning(
                "⚠ Exemption enabled but no limit set for %s (%s)",
                employee.name,
                prev_year
            )

        # ----------------------------------------
        # 🔵 NORMAL RULE (DEFAULT)
        # ----------------------------------------
        carry_days = min(remaining_days, annual_type.carry_forward_max or 7)

        _logger.info(
            "📦 Standard Carry | %s | Remaining=%s | Carry=%s",
            employee.name,
            remaining_days,
            carry_days
        )

        return carry_days

    def _compute_bonus_leave(self, employee):
        if not employee.date_of_join:
            _logger.warning("No join date for %s, bonus=0", employee.name)
            print(f"No join date for {employee.name}")
            return 0

        years = date.today().year - employee.date_of_join.year
        if years >= 5:
            bonus = 3
        elif years == 4:
            bonus = 2
        elif years == 3:
            bonus = 1
        else:
            bonus = 0

        _logger.info("Bonus for %s: %s days (years: %s)", employee.name, bonus, years)
        print(f"Bonus for {employee.name}: {bonus} (years: {years})")
        return bonus

    def _create_allocation(self, employee, leave_type, days, year, allocation_type, alloc_type):
        if days <= 0:
            return

        name = f"{leave_type.name} - {allocation_type} - {employee.name}"
        allocation = self.env['hr.leave.allocation'].create({
            'name': name,
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': days,
            'date_from': date(year, 1, 1),
            'date_to': date(year, 12, 31),
            'allocation_type': alloc_type,
        })
        allocation.action_validate()
        _logger.info("📝 Created allocation for %s: %s days (%s)", employee.name, days, alloc_type)
        print(f"Created allocation for {employee.name}: {days} days ({alloc_type})")

    @api.model
    def send_leave_balance_alerts(self):
        _logger.info("📧 Starting monthly leave balance alerts")
        self._send_leave_balance_mails(10)
        self._send_leave_balance_mails(15)
        _logger.info("✅ Monthly leave balance alerts completed")

    def _send_leave_balance_mails(self, threshold):
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('work_location_id.name', '=', 'Dubai'),
        ])

        manager_data = {}
        hr_data = []

        current_year = fields.Date.today().year
        annual_types = self.search([
            ('annual_leave_boolean', '=', True),
            ('name', 'ilike', f'%{current_year}%')
        ])

        if not annual_types:
            return

        for emp in employees:
            balance = sum(emp._get_remaining_leave(t, current_year) for t in annual_types)

            if balance < threshold:
                continue

            if emp.work_email:
                self.env.ref('tg_holidays.mail_template_leave_balance_employee').with_context(
                    balance=balance,
                    threshold=threshold
                ).send_mail(emp.id)

            if emp.parent_id:
                manager_data.setdefault(emp.parent_id, []).append({
                    'name': emp.name,
                    'balance': balance,
                })

            hr_data.append({
                'name': emp.name,
                'balance': balance,
            })

        for manager, emp_list in manager_data.items():
            if manager.work_email:
                self.env.ref('tg_holidays.mail_template_leave_balance_manager').with_context(
                    employees=emp_list,
                    threshold=threshold
                ).send_mail(manager.id)

        hr_users = self.env.ref('hr.group_hr_manager').users
        emails = ','.join(u.partner_id.email for u in hr_users if u.partner_id.email)

        if hr_data and emails:
            hr_employee = self.env['hr.employee'].search([], limit=1)
            self.env.ref('tg_holidays.mail_template_leave_balance_hr').with_context(
                employees=hr_data,
                threshold=threshold
            ).send_mail(hr_employee.id, email_values={'email_to': emails})

        self.env.cr.commit()


class HrLeaveExemptionLine(models.Model):
    _name = 'hr.leave.exemption.line'
    _description = 'Leave Exemption Limit'

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='cascade'
    )

    year = fields.Integer(
        string="Year",
        required=True
    )

    exemption_limit = fields.Float(
        string="Exemption Limit (Days)",
        required=True
    )

    _sql_constraints = [
        (
            'employee_year_unique',
            'unique(employee_id, year)',
            'Exemption limit for this year already exists for this employee.'
        )
    ]

class HrLeaveApprovalFlow(models.Model):
    _name = 'hr.leave.approval.flow'
    _description = 'Leave Approval Flow'
    _order = 'sequence'

    leave_type_id = fields.Many2one(
        'hr.leave.type',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string="Level",
        required=True,
        default=1
    )

    group_ids = fields.Many2many(
        'res.groups',
        string="Approver Groups",
        required=True
    )

    is_final = fields.Boolean(
        string="Final Approval"
    )
