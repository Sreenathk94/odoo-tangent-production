# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    current_employee_cost = fields.Float(
        "Employee Cost",
        readonly=True,
        help="Cost per hour from the Employee Cost record.",
    )

    total_employee_cost = fields.Float(
        "Total Employee Cost",
        readonly=True,
        help="Total cost = Employee cost * Hours spent.",
    )

    stage_fee = fields.Float("Stage Fee", readonly=True)
    # total_stage_fee = fields.Float("Total Stage Fee", readonly=True)
    # total_project_stage_fee = fields.Float("Total Project + Stage Fee",
    #                                        readonly=True)

    @api.model
    def _select(self):
        return super()._select() + """
            ,
            (
                SELECT COALESCE(l.cost, 0.0)
                FROM hr_employee_cost_line l
                JOIN hr_employee_cost c ON l.cost_id = c.id
                WHERE l.employee_id = A.employee_id
                  AND c.state = 'confirmed'
                  AND A.date BETWEEN c.date_from AND c.date_to
                ORDER BY c.date_from DESC
                LIMIT 1
            ) AS current_employee_cost,

            (
                A.unit_amount * COALESCE((
                    SELECT COALESCE(l.cost, 0.0)
                    FROM hr_employee_cost_line l
                    JOIN hr_employee_cost c ON l.cost_id = c.id
                    WHERE l.employee_id = A.employee_id
                      AND c.state = 'confirmed'
                      AND A.date BETWEEN c.date_from AND c.date_to
                    ORDER BY c.date_from DESC
                    LIMIT 1
                ), 0.0)
            ) AS total_employee_cost,

            -- Stage Fee
            (
                SELECT COALESCE(s.total_amount, 0.0)
                FROM project_cost_stage s
                WHERE s.project_id = A.project_id
                  AND s.timesheet_status_id = A.timesheet_status_id
                LIMIT 1
            ) AS stage_fee
        """
