from odoo import http
from odoo.http import request
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError


class CustomHrAttendanceController(http.Controller):

    @http.route('/custom_hr_attendance/get_filtered_attendance', type='json',
                auth='user')
    def get_filtered_attendance(self, filterValue, start_date, end_date):
        if filterValue == 'today':
            # start_time = datetime.combine(datetime.today(), time.min)
            # end_time = datetime.combine(datetime.today(), time.max)
            employee_date = {}
            records_data = []
            total_positive_cost = 0
            total_negative_cost = 0
            records = request.env['hr.attendance'].sudo().search([],
                                                                 order='check_in DESC')
            for rec in records:
                if rec.employee_id.id not in employee_date:
                    employee_date[rec.employee_id.id] = {
                        'employee_id': rec.employee_id.id,
                        'name': rec.employee_id.name,
                        'department': [rec.employee_id.department_id.name,
                                       rec.employee_id.department_id.id],
                        'total_hours': round(rec.worked_hours, 2),
                        'total_working_days': 1,
                        'cost_per_hour': rec.employee_id.hourly_cost,
                    }
            for data in employee_date.values():
                avg_hours = data['total_hours'] / data['total_working_days']
                data['avg'] = round(avg_hours, 2)
                data['positive_value'] = round(
                    avg_hours - 9 if avg_hours > 9 else 0, 2)
                data['negative_value'] = round(
                    9 - avg_hours if avg_hours < 9 else 0, 2)
                data['positive_cost'] = round(
                    data['positive_value'] * data['cost_per_hour'], 2)
                data['negative_cost'] = round(
                    data['negative_value'] * data['cost_per_hour'], 2)

                # Update total costs
                total_positive_cost += data['positive_cost']
                total_negative_cost += data['negative_cost']

                records_data.append(data)
            return {
                "records": records_data,
                "total_positive_cost": round(total_positive_cost, 2),
                "total_negative_cost": round(total_negative_cost, 2)
            }
        elif filterValue == 'week':
            today = datetime.today()
            start_time = datetime.combine(
                today - timedelta(days=today.weekday() + 1), time.min)
            end_time = datetime.combine(start_time + timedelta(days=6),
                                        time.max)

        elif filterValue == 'month':
            today = datetime.today()
            start_time = datetime.combine(today.replace(day=1), time.min)
            next_month = today.replace(day=28) + timedelta(days=4)
            end_time = datetime.combine(
                next_month.replace(day=1) - timedelta(days=1), time.max)

        elif filterValue == 'custom':
            start_time = datetime.strptime(start_date, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0)
            end_time = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23,
                                                                       minute=59,
                                                                       second=59)

        records_data = []
        total_positive_cost = 0
        total_negative_cost = 0

        if start_time and end_time:
            records = request.env['hr.attendance'].sudo().search(
                [('check_in', ">=", start_time), ('check_in', "<=", end_time)]
            )
            employee_data = {}

            for rec in records:
                employee_id = rec.employee_id.id
                if employee_id not in employee_data:
                    employee_data[employee_id] = {
                        'employee_id': employee_id,
                        'name': rec.employee_id.name,
                        'department': [rec.employee_id.department_id.name,
                                       rec.employee_id.department_id.id],
                        'total_hours': round(rec.worked_hours, 2),
                        'total_working_days': 1,
                        'cost_per_hour': rec.employee_id.hourly_cost,
                    }
                else:
                    employee_data[employee_id][
                        'total_hours'] += rec.worked_hours
                    employee_data[employee_id]['total_working_days'] += 1

            for data in employee_data.values():
                avg_hours = data['total_hours'] / data['total_working_days']
                data['avg'] = round(avg_hours, 2)
                data['positive_value'] = round(
                    avg_hours - 9 if avg_hours > 9 else 0, 2)
                data['negative_value'] = round(
                    9 - avg_hours if avg_hours < 9 else 0, 2)
                data['positive_cost'] = round(
                    data['positive_value'] * data['cost_per_hour'], 2)
                data['negative_cost'] = round(
                    data['negative_value'] * data['cost_per_hour'], 2)

                # Update total costs
                total_positive_cost += data['positive_cost']
                total_negative_cost += data['negative_cost']

                records_data.append(data)

        return {
            "records": records_data,
            "total_positive_cost": round(total_positive_cost, 2),
            "total_negative_cost": round(total_negative_cost, 2)
        }
