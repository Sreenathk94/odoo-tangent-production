from odoo import api, fields, models, _
import mysql.connector
from odoo import exceptions
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import pytz

class ResCompany(models.Model):
    _inherit = "res.company"

    db_hostname = fields.Char(string='IP Address of Host', required=True, tracking=True)
    db_name = fields.Char(string='Database Name', required=True, tracking=True)
    db_port = fields.Integer(string='Port', tracking=True)
    db_username = fields.Char(string='Username', required=True, tracking=True)
    db_password = fields.Char(string='Password', required=True)
    db_test_query = fields.Text(string='Fetch Query', required=True, default='SELECT * FROM tmp_attendance;', tracking=True)
    db_query_result = fields.Text(string='Connection Result', readonly=True)
    fetch_date = fields.Date(string='Fetch Date', required=True, tracking=True)

    def run_testquery(self):
        try:
            con = mysql.connector.connect(
                host=self.db_hostname,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password,
                auth_plugin='mysql_native_password'
            )

            cursor = con.cursor()
            cursor.execute(self.db_test_query)
            recordss = cursor.fetchall()
            self.db_query_result = recordss
            con.close()
            cursor.close()

        except Exception as e:
            raise ValidationError(_('Error reading data from MySQL table'))
            raise exceptions.Warning('Warning message', e)

        finally:
            con = mysql.connector.connect(
                host=self.db_hostname,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password,
                auth_plugin='mysql_native_password'
            )
            if con.is_connected():
                con.close()

    def fetch_attendance_data(self):
        self = self.env['res.company'].search([('id', '=', 1)])
        
        # Set Asia/Dubai timezone and UTC timezone
        dubai_tz = pytz.timezone('Asia/Dubai')
        utc_tz = pytz.utc
        
        try:
            con = mysql.connector.connect(
                host=self.db_hostname,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password,
                auth_plugin='mysql_native_password'
            )

            cursor = con.cursor()
            cursor.execute(self.db_test_query)
            recordss = cursor.fetchall()
            date_recordss = [record for record in recordss if record[0] == self.fetch_date]
            employee_ids = self.env['hr.employee'].search([])

            for employee in employee_ids:
                result_set = [record for record in date_recordss if record[3] == employee.bio_code]
                
                if result_set:
                    lines = []
                    for result in result_set:
                        # Handle invalid times (1970, missing times)
                        if result[1].year == 1970 or result[2].year == 1970:
                            employee.missing_count += 1
                        else:
                            # Convert check_in and check_out to Asia/Dubai timezone first
                            check_in_dubai = dubai_tz.localize(result[1]) if result[1].tzinfo is None else result[1]
                            check_out_dubai = dubai_tz.localize(result[2]) if result[2].tzinfo is None else result[2]

                            # Convert check_in and check_out to UTC
                            check_in_utc = check_in_dubai.astimezone(utc_tz)
                            check_out_utc = check_out_dubai.astimezone(utc_tz)

                            # Append to lines
                            lines.append((0, 0, {
                                'check_in': check_in_utc,
                                'check_out': check_out_utc
                            }))

                    first_check_in = min(result_set, key=lambda x: x[1])
                    last_check_out = max(result_set, key=lambda x: x[2])
                    first_check_in_utc = dubai_tz.localize(first_check_in[1]).astimezone(utc_tz)
                    last_check_out_utc = dubai_tz.localize(last_check_out[2]).astimezone(utc_tz) if last_check_out[2].year != 1970 else dubai_tz.localize(last_check_out[1]).astimezone(utc_tz)
                    self.env['hr.attendance'].create({
                        'fetch_date': self.fetch_date,
                        'employee_id': employee.id,
                        'line_ids': lines,
                        'check_in': first_check_in_utc,
                        'check_out': last_check_out_utc
                    })

            # Increment the fetch date
            self.fetch_date = self.fetch_date + relativedelta(days=1)
            
            con.close()
            cursor.close()

        except Exception as e:
            raise ValidationError(_(e))

        finally:
            con = mysql.connector.connect(
                host=self.db_hostname,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password,
                auth_plugin='mysql_native_password'
            )
            if con.is_connected():
                con.close()
