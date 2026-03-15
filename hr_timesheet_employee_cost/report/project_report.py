# -*- coding: utf-8 -*-
from odoo import fields, models, api, tools


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    current_employee_cost = fields.Float('Employee Cost', readonly=True)
    total_employee_cost = fields.Float('Total Employee Cost', readonly=True)

    # NEW FIELDS
    stage_fee = fields.Float("Stage Fee", readonly=True)
    # total_stage_fee = fields.Float("Total Stage Fee", readonly=True)
    # total_project_stage_fee = fields.Float("Total Project + Stage Fee",
    #                                        readonly=True)

    @api.model
    def _select(self):
        return super()._select() + """
            ,
            -- Employee hourly cost
            (
                SELECT COALESCE(l.cost, 0.0)
                FROM hr_employee_cost_line l
                JOIN hr_employee_cost c ON l.cost_id = c.id
                WHERE l.employee_id = employee_id
                  AND c.state = 'confirmed'
                ORDER BY c.date_from DESC
                LIMIT 1
            ) AS current_employee_cost,

            -- Total employee cost = total hours * hourly rate
            (
                total_hours_spent * COALESCE((
                    SELECT COALESCE(l.cost, 0.0)
                    FROM hr_employee_cost_line l
                    JOIN hr_employee_cost c ON l.cost_id = c.id
                    WHERE l.employee_id = employee_id
                      AND c.state = 'confirmed'
                    ORDER BY c.date_from DESC
                    LIMIT 1
                ), 0.0)
            ) AS total_employee_cost,

            -- Stage Fee: from project_cost_stage where stage matches the project stage
              (
                SELECT COALESCE(s.total_amount, 0.0)
                FROM project_cost_stage s
                WHERE s.project_id = project_id
                AND s.timesheet_status_id = timesheet_status_id
                LIMIT 1
            ) AS stage_fee
            
           

        """

class ProjectStageTimesheetReport(models.Model):
    _name = 'project.stage.timesheet.report'
    _description = 'Project Stage Fee, Employee Cost & Timesheet Pivot'
    _auto = False

    project_id = fields.Many2one('project.project', readonly=True)
    stage_id = fields.Many2one('hr.timesheet.status', string='Stage', readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)

    hours = fields.Float(string='Hours', readonly=True)
    stage_fees = fields.Float(string='Stage Fee', readonly=True)
    employee_cost = fields.Float(string='Employee Cost', readonly=True)
    total_employee_cost = fields.Float(string='Total Employee Cost', readonly=True)

    percentage = fields.Float(string='Cost % of Stage Fee', readonly=True)
    color = fields.Selection([
        ('none', 'None'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('red', 'Red'),
    ], readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)

        self._cr.execute("""
            CREATE OR REPLACE VIEW project_stage_timesheet_report AS (

                WITH employee_cost_rate AS (
                    SELECT DISTINCT ON (l.employee_id)
                        l.employee_id,
                        l.cost AS rate
                    FROM hr_employee_cost_line l
                    JOIN hr_employee_cost c ON c.id = l.cost_id
                    WHERE c.state = 'confirmed'
                    ORDER BY l.employee_id, c.date_from DESC
                )

                SELECT
                    ROW_NUMBER() OVER () AS id,
                    base.project_id,
                    base.stage_id,
                    base.hours,
                    base.stage_fees,
                    base.employee_cost,
                    base.total_employee_cost,
                    base.percentage,
                    base.color
                FROM (
                    -- 1) Stages that have actual timesheet entries
                    SELECT
                        p.id AS project_id,
                        aal.status_id AS stage_id,
                        COALESCE(SUM(aal.unit_amount), 0.0) AS hours,
                        COALESCE(MAX(s.total_amount), 0.0) AS stage_fees,
                        COALESCE(SUM(COALESCE(rate.rate, 0.0)), 0.0) AS employee_cost,
                        COALESCE(SUM(aal.unit_amount * COALESCE(rate.rate, 0.0)), 0.0) AS total_employee_cost,
                        CASE
                            WHEN MAX(s.total_amount) IS NULL OR MAX(s.total_amount) = 0 THEN 0
                            ELSE
                                ( SUM(aal.unit_amount * COALESCE(rate.rate, 0.0))
                                  / MAX(s.total_amount)
                                ) * 100
                        END AS percentage,
                        CASE
                            WHEN MAX(s.total_amount) IS NULL OR MAX(s.total_amount) = 0 THEN 'none'
                            WHEN (
                                SUM(aal.unit_amount * COALESCE(rate.rate, 0.0))
                                / MAX(s.total_amount)
                            ) * 100 <= 50 THEN 'green'
                            WHEN (
                                SUM(aal.unit_amount * COALESCE(rate.rate, 0.0))
                                / MAX(s.total_amount)
                            ) * 100 <= 75 THEN 'yellow'
                            WHEN (
                                SUM(aal.unit_amount * COALESCE(rate.rate, 0.0))
                                / MAX(s.total_amount)
                            ) * 100 >= 90 THEN 'red'
                            ELSE 'none'
                        END AS color
                    FROM project_project p
                    LEFT JOIN account_analytic_line aal
                        ON aal.project_id = p.id
                    LEFT JOIN project_cost_stage s
                        ON s.project_id = p.id
                       AND s.timesheet_status_id = aal.status_id
                    LEFT JOIN employee_cost_rate rate
                       ON rate.employee_id = aal.employee_id
                    GROUP BY
                        p.id,
                        aal.status_id

                    UNION

                    -- 2) Stages selected in Time Management but with NO timesheets
                    SELECT
                        p.id AS project_id,
                        stage_rel.hr_timesheet_status_id AS stage_id,
                        0.0 AS hours,
                        COALESCE(MAX(s.total_amount), 0.0) AS stage_fees,
                        0.0 AS employee_cost,
                        0.0 AS total_employee_cost,
                        0.0 AS percentage,
                        'none' AS color
                    FROM project_project p
                    JOIN allowed_stage_project_rel stage_rel
                        ON stage_rel.project_project_id = p.id
                    LEFT JOIN project_cost_stage s
                        ON s.project_id = p.id
                       AND s.timesheet_status_id = stage_rel.hr_timesheet_status_id
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM account_analytic_line aal
                        WHERE aal.project_id = p.id
                          AND aal.status_id = stage_rel.hr_timesheet_status_id
                    )
                    GROUP BY
                        p.id,
                        stage_rel.hr_timesheet_status_id
                ) AS base
            )
        """)
