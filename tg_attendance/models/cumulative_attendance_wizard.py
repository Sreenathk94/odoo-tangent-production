from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
from io import StringIO
import csv
from datetime import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class CumulativeAttendanceWizard(models.TransientModel):
    _name = "cumulative.attendance.wizard"
    _description = "Import Cumulative Attendance CSV"

    file = fields.Binary(string="CSV File", required=True)
    filename = fields.Char("Filename")

    def import_attendance_csv(self):
        """Import or update attendance data from CSV."""
        try:
            csv_data = base64.b64decode(self.file)
            csv_text = csv_data.decode("utf-8-sig").replace("\r", "")
            csv_io = StringIO(csv_text)
            reader = csv.reader(csv_io)
            rows = list(reader)

            if not rows or len(rows) < 2:
                raise ValidationError(_("CSV file appears empty or invalid."))

            # Find actual header row dynamically
            header_row = None
            for r in rows:
                if r and "Employee ID" in [c.strip() for c in r]:
                    header_row = r
                    break
            if not header_row:
                raise ValidationError(_("Missing required column: Employee ID"))

            header = [h.strip().replace("\ufeff", "") for h in header_row]
            start_index = rows.index(header_row) + 1
            valid_rows = [r for r in rows[start_index:] if len(r) > 2]

            def find_col(name):
                for i, h in enumerate(header):
                    if h.lower() == name.lower():
                        return i
                raise ValidationError(_(f"Missing required column: {name}"))

            idx_id = find_col("Employee ID")
            idx_name = find_col("Employee Name")
            idx_date = find_col("Date")
            idx_state = find_col("State")
            idx_timelog = find_col("Time Log")

            dubai_tz = pytz.timezone("Asia/Dubai")
            utc_tz = pytz.utc

            for i in range(0, len(valid_rows), BATCH_SIZE):
                batch = valid_rows[i:i + BATCH_SIZE]
                _logger.info("Processing batch %s - %s", i, i + len(batch))

                for row in batch:
                    try:
                        emp_code = str(row[idx_id]).strip()
                        emp_name = row[idx_name].strip()
                        date_str = row[idx_date].strip()
                        state = row[idx_state].strip().upper()
                        timelog_str = row[idx_timelog].strip()

                        if not date_str:
                            continue
                        att_date = datetime.strptime(date_str, "%d-%b-%Y").date()

                        if state in ("A", "H") or not timelog_str or "Absent" in timelog_str:
                            continue

                        employee = self.env["hr.employee"].search([("bio_code", "=", emp_code)], limit=1)
                        if not employee:
                            _logger.warning("Employee not found for code %s (%s)", emp_code, emp_name)
                            continue

                        # Parse time log pairs
                        lines = []
                        pairs = [p.strip() for p in timelog_str.split(",") if "->" in p]
                        for pair in pairs:
                            check_in_str, check_out_str = pair.split("->")
                            check_in_dt = dubai_tz.localize(datetime.combine(
                                att_date, datetime.strptime(check_in_str.strip(), "%H:%M:%S").time()))
                            check_out_dt = dubai_tz.localize(datetime.combine(
                                att_date, datetime.strptime(check_out_str.strip(), "%H:%M:%S").time()))

                            check_in_utc = check_in_dt.astimezone(utc_tz).replace(tzinfo=None)
                            check_out_utc = check_out_dt.astimezone(utc_tz).replace(tzinfo=None)

                            lines.append((0, 0, {
                                "check_in": check_in_utc,
                                "check_out": check_out_utc,
                            }))

                        if not lines:
                            continue

                        check_in_final = lines[0][2]["check_in"]
                        check_out_final = lines[-1][2]["check_out"]

                        # 🔍 Check if attendance already exists
                        attendance = self.env["hr.attendance"].search([
                            ("employee_id", "=", employee.id),
                            ("fetch_date", "=", att_date),
                        ], limit=1)

                        if attendance:
                            # ✅ UPDATE if missing pairs or incomplete
                            existing_lines = attendance.line_ids
                            existing_pairs = {(l.check_in, l.check_out) for l in existing_lines}

                            new_pairs = {(l[2]["check_in"], l[2]["check_out"]) for l in lines}
                            missing_pairs = new_pairs - existing_pairs

                            if missing_pairs:
                                for pair in missing_pairs:
                                    self.env["attendance.line"].create({
                                        "attendance_id": attendance.id,
                                        "check_in": pair[0],
                                        "check_out": pair[1],
                                    })

                                # Update overall check-in/out if needed
                                attendance.check_in = min(
                                    attendance.check_in, check_in_final
                                ) if attendance.check_in else check_in_final
                                attendance.check_out = max(
                                    attendance.check_out, check_out_final
                                ) if attendance.check_out else check_out_final

                                _logger.info("Updated existing attendance for %s on %s", emp_name, att_date)
                            else:
                                _logger.info("No updates needed for %s on %s", emp_name, att_date)
                        else:
                            # 🆕 Create new attendance
                            self.env["hr.attendance"].create({
                                "employee_id": employee.id,
                                "fetch_date": att_date,
                                "check_in": check_in_final,
                                "check_out": check_out_final,
                                "line_ids": lines,
                            })
                            _logger.info("Created new attendance for %s on %s", emp_name, att_date)

                    except Exception as row_err:
                        _logger.error("Error processing row %s: %s", row, row_err)

                self.env.cr.commit()

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Attendance Import Complete"),
                    "message": _("Attendance imported or updated successfully."),
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            raise ValidationError(_("Error processing file: %s") % str(e))