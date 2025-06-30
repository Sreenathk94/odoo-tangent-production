from datetime import timedelta
from odoo import api, fields, models, _
import mysql.connector
from odoo.exceptions import ValidationError
import pytz
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

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
            con=mysql.connector.connect(host=self.db_hostname,
                                        database=self.db_name,
                                        user=self.db_username,
                                        password=self.db_password,
                                        auth_plugin='mysql_native_password')

            cursor=con.cursor()
            cursor.execute(self.db_test_query)
            recordss=cursor.fetchall()
            self.db_query_result=recordss
            con.close()
            cursor.close()

        except Exception as e:
            raise ValidationError(_('Error reading data from MySQL table'))
            raise exceptions.Warning('Warning message',e)

        finally:
            con = mysql.connector.connect(host=self.db_hostname,
                                          database=self.db_name,
                                          user=self.db_username,
                                          password=self.db_password,
                                          auth_plugin='mysql_native_password')
            if (con.is_connected()):
                con.close()

    def fetch_attendance_data(self):
        self = self.env['res.company'].search([('id', '=', 1)])

        # Set Asia/Dubai timezone and UTC timezone
        dubai_tz = pytz.timezone('Asia/Dubai')
        utc_tz = pytz.utc

        try:
            # Connect to MySQL database
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
                            # Ensure result[1] and result[2] are aware of the Dubai timezone
                            check_in = result[1].replace(tzinfo=dubai_tz) if result[1].tzinfo is None else result[1]
                            check_out = result[2].replace(tzinfo=dubai_tz) if result[2].tzinfo is None else result[2]

                            # Convert to UTC, make naive, and deduct 19 minutes
                            check_in_utc_naive = check_in.astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19)
                            check_out_utc_naive = check_out.astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19)

                            # Append to lines
                            lines.append((0, 0, {
                                'check_in': check_in_utc_naive,
                                'check_out': check_out_utc_naive
                            }))

                    # Calculate first check-in and last check-out in UTC (naive) and deduct 19 minutes
                    first_check_in = min(result_set, key=lambda x: x[1])
                    last_check_out = max(result_set, key=lambda x: x[2])
                    first_check_in_utc_naive = (
                        first_check_in[1].replace(tzinfo=dubai_tz).astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19)
                    )
                    last_check_out_utc_naive = (
                        (last_check_out[2].replace(tzinfo=dubai_tz).astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19))
                        if last_check_out[2].year != 1970
                        else (last_check_out[1].replace(tzinfo=dubai_tz).astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19))
                    )

                    # Create attendance record
                    self.env['hr.attendance'].create({
                        'fetch_date': self.fetch_date,
                        'employee_id': employee.id,
                        'line_ids': lines,
                        'check_in': first_check_in_utc_naive,
                        'check_out': last_check_out_utc_naive
                    })

            # Increment the fetch date
            self.fetch_date = self.fetch_date + relativedelta(days=1)

            con.close()
            cursor.close()

        except Exception as e:
            raise ValidationError(_(e))

        finally:
            # Ensure the connection is closed
            if con.is_connected():
                con.close()

    def fetch_missed_attendance_data(self):
        _logger.info("Starting missed attendance fetch...")

        self = self.env['res.company'].search([('id', '=', 1)])
        dubai_tz = pytz.timezone('Asia/Dubai')
        utc_tz = pytz.utc

        con = None
        cursor = None

        try:
            today = fields.Date.today()
            first_day = today.replace(day=1)

            # Get all attendance fetch_dates for this month till today
            existing_dates = self.env['hr.attendance'].search([
                ('fetch_date', '>=', first_day),
                ('fetch_date', '<=', today)
            ]).mapped('fetch_date')

            # Generate all dates in current month up to today
            all_dates = set(first_day + timedelta(days=i) for i in range((today - first_day).days + 1))
            missing_dates = sorted(all_dates - set(existing_dates))

            _logger.info("Missing attendance dates this month: %s",
                         ", ".join([str(d) for d in missing_dates]) or "None")

            # Connect to external DB
            con = mysql.connector.connect(
                host=self.db_hostname,
                database=self.db_name,
                user=self.db_username,
                password=self.db_password,
                auth_plugin='mysql_native_password'
            )
            cursor = con.cursor()

            employee_ids = self.env['hr.employee'].search([])

            for missing_date in missing_dates:
                _logger.info("Fetching data for: %s", missing_date)
                sql_date = missing_date.strftime('%Y-%m-%d')
                cursor.execute(f"SELECT * FROM attendance WHERE workdate = '{sql_date}'")
                records = cursor.fetchall()

                if not records:
                    _logger.info("No data for %s in external DB", sql_date)
                    continue

                for employee in employee_ids:
                    emp_records = [rec for rec in records if rec[3] == employee.bio_code]
                    if not emp_records:
                        continue

                    lines = []
                    for rec in emp_records:
                        if rec[1].year == 1970 or rec[2].year == 1970:
                            employee.missing_count += 1
                            _logger.info("Invalid time for %s on %s", employee.name, sql_date)
                            continue

                        check_in = rec[1].replace(tzinfo=dubai_tz) if rec[1].tzinfo is None else rec[1]
                        check_out = rec[2].replace(tzinfo=dubai_tz) if rec[2].tzinfo is None else rec[2]

                        check_in_utc = check_in.astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19)
                        check_out_utc = check_out.astimezone(utc_tz).replace(tzinfo=None) - timedelta(minutes=19)

                        lines.append((0, 0, {
                            'check_in': check_in_utc,
                            'check_out': check_out_utc,
                        }))

                    if not lines:
                        continue

                    first_check_in = min(emp_records, key=lambda r: r[1])
                    last_check_out = max(emp_records, key=lambda r: r[2])

                    first_utc = first_check_in[1].replace(tzinfo=dubai_tz).astimezone(utc_tz).replace(
                        tzinfo=None) - timedelta(minutes=19)
                    last_utc = (
                        last_check_out[2].replace(tzinfo=dubai_tz).astimezone(utc_tz).replace(tzinfo=None) - timedelta(
                            minutes=19)
                        if last_check_out[2].year != 1970 else first_utc
                    )

                    self.env['hr.attendance'].create({
                        'fetch_date': missing_date,
                        'employee_id': employee.id,
                        'line_ids': lines,
                        'check_in': first_utc,
                        'check_out': last_utc
                    })
                    _logger.info("Created attendance for %s on %s", employee.name, missing_date)

            _logger.info("Completed fetching all missed attendances.")

        except Exception as e:
            _logger.exception("Failed to fetch missed attendance: %s", str(e))
            raise ValidationError(_("Missed attendance fetch failed: %s") % str(e))

        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()
            _logger.info("MySQL connection closed.")
