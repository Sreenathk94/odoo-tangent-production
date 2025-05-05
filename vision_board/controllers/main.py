from odoo import http
from odoo.http import request
from datetime import datetime


class VisionBoardController(http.Controller):
    @http.route('/vision_board/employee_data', type='json', auth='user')
    def get_employee_data(self, month=None, year=None):
        """Endpoint to get employee data for the dashboard"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No employee found for current user'}
        
        # If month and year are not provided, use current date
        if not month or not year:
            current_date = datetime.now()
            month = current_date.month
            year = current_date.year
        
        return employee.get_employee_dashboard_data( month, year)

    @http.route('/vision_board/privacy_policy', type='json', auth='user')
    def get_privacy_policy(self):
        try:
            company = request.env.company
            return {
                'content': company.privacy_policy_content or '',
                'last_updated': company.privacy_policy_last_updated,
                'privacy_policy_pdf': company.privacy_policy_pdf,
                'privacy_policy_filename': company.privacy_policy_filename,
                'company_id': company.id
            }
        except Exception as e:
            return {'error': str(e)}