from odoo.http import Controller, route, request
from datetime import datetime, timedelta, time
from odoo import fields
from pytz import timezone, utc


class AttendanceClaim(Controller):
    def float_to_time(self,float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    @route('/attendance', auth='user', website=True)
    def attendance(self, **kwargs):
        if kwargs.get('employee_id') and kwargs.get('date'):
            data_to_load_html_template = []
            employee_id = request.env['hr.employee'].sudo().browse(int(kwargs.get('employee_id')))
            if 1 == 1:
            # if employee_id.user_id.id == request.env.user.id:
                sterday = datetime.strptime(kwargs.get('date'), '%d-%b-%Y')
                for attendance in request.env['hr.attendance'].search([
                    ('fetch_date', '=', sterday),
                    ('employee_id', '=', employee_id.id)
                ]).filtered(
                    lambda a: a.actual_hours < request.env.company.attend_work_hrs)[
                    0]:
                    i = 4
                    j = 1
                    k = len(attendance.line_ids)
                    data_to_load_html_template.append([
                        'First Check-in & Last Check-out',
                        (attendance.check_in + timedelta(hours=5.5)).strftime(
                            "%d-%m-%Y %H:%M:%S"),
                        (attendance.check_out + timedelta(hours=5.5)).strftime(
                            "%d-%m-%Y %H:%M:%S"),
                        self.float_to_time(attendance.worked_hours),
                        ' ',
                    ])
                    if attendance.employee_id.location_id.detect_lunch == True:
                        if any(x.check_out.time() > time(13,
                                                         0) and x.check_out.time() < time(
                                14, 0) for x in attendance.line_ids) and any(
                                x.check_in.time() > time(13,
                                                         0) and x.check_in.time() < time(
                                        14, 0) for x in attendance.line_ids):
                            pass
                        else:
                            data_to_load_html_template.append([
                                'Less 1 hour for the lunch break', ' ', ' ',
                                self.float_to_time(-1)
                            ])
                    row_3 = ['Total time excluding break', ' ', ' ']
                    if attendance.employee_id.location_id.detect_lunch == True:
                        if any(x.check_out.time() > time(13,0) and x.check_out.time() < time(
                                14, 0) for x in attendance.line_ids) and any(
                                x.check_in.time() > time(13,
                                                         0) and x.check_in.time() < time(
                                        14, 0) for x in attendance.line_ids):
                            row_3.append(
                                self.float_to_time((attendance.worked_hours)))
                        else:
                            row_3.append(self.float_to_time(
                                (attendance.worked_hours - 1)))
                    else:
                        row_3.append(
                            self.float_to_time((attendance.worked_hours)))
                    row_3.append(' ')
                    data_to_load_html_template.append(row_3)
                    data_to_load_html_template.append([
                        'Breaks', ' ', ' ', 'Counted', 'Non-Counted'
                    ])
                    check_out = False;
                    non_count = timedelta(days=0);
                    count = timedelta(days=0)
                    row = [' ', ' ', ' ', ' ', ' ']
                    for line in attendance.line_ids:
                        if j != 1:
                            row[2] = (line.check_in + timedelta(
                                hours=5.5)).strftime("%d-%m-%Y %H:%M:%S")
                            dif = (line.check_in + timedelta(
                                hours=5.5)) - check_out
                            hours = int(dif.seconds / 3600)
                            minutes = (dif.seconds % 3600) / 60
                            if hours == 0 and minutes <= 15:
                                row[4] = str(dif)
                                non_count += dif
                            else:
                                row[3] = str(dif)
                                count += dif
                            data_to_load_html_template.append(row)
                        if k != j:
                            row = [' ', ' ', ' ', ' ', ' ', 'claim']
                            row[0] = 'Break ' + str(j)
                            row[1] = (line.check_out + timedelta(
                                hours=5.5)).strftime("%d-%m-%Y %H:%M:%S")
                            check_out = line.check_out + timedelta(hours=5.5)
                        i += 1
                        j += 1
                    data_to_load_html_template.append([
                        'Total Breaks', ' ', ' ', str(count), ' '
                    ])
                    wk_hr = timedelta(hours=attendance.worked_hours)
                    if attendance.employee_id.location_id.detect_lunch == True:
                        if any(x.check_out.time() > time(13,
                                                         0) and x.check_out.time() < time(
                                14, 0) for x in attendance.line_ids) and any(
                                x.check_in.time() > time(13,
                                                         0) and x.check_in.time() < time(
                                        14, 0) for x in attendance.line_ids):
                            bk_hr = count
                        else:
                            bk_hr = count + timedelta(hours=1)
                    else:
                        bk_hr = count
                    data_to_load_html_template.append([
                        'Net total time inside the office (' + str(
                            self.float_to_time(
                                attendance.worked_hours)) + ' - ' + str(
                            count) + ')', ' ', ' ', str(wk_hr - bk_hr), ' '
                    ])
                    return request.render(
                        "tg_attendance.attendance_claim_view", {
                            'datas': data_to_load_html_template,
                            'attend_work_hrs':request.env.company.attend_work_hrs,
                            'sterday': sterday,
                            'name': employee_id.name,
                            'id': employee_id.id,
                            'base_url': '/attendance/claim/form'
                        })
        return request.redirect('/web')

    @route('/submit/claim/attendance', auth='user', website=True)
    def create_attendance_request(self, **post):
        if post.get('date_from') and post.get('date_to') and post.get('employee_id'):
            # Define Dubai timezone
            dubai_tz = timezone('Asia/Dubai')

            # Parse the input datetime and convert to UTC
            date_from = dubai_tz.localize(
                datetime.strptime(post.get('date_from'), '%Y-%m-%d %H:%M:%S')).astimezone(utc)
            date_to = dubai_tz.localize(
                datetime.strptime(post.get('date_to'), '%Y-%m-%d %H:%M:%S')).astimezone(utc)

            employee_id = request.env['hr.employee'].sudo().browse(
                int(post.get('employee_id')))

            approval_id = request.env['attendance.claim.approval'].search([
                ('employee_id', '=', employee_id.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to)
            ])
            if approval_id:
                return request.render(
                    "tg_attendance.attendance_claim_view_from_confirm_view",
                    {'reference': approval_id, 'show_reclaim': approval_id.show_reclaim, 'show_form': False})
            index = int(post.get('index'))
            hours = int(post.get('request_hour', 0))
            minutes = int(post.get('request_minutes', 0))
            time_float = hours + (minutes / 60)
            approval_id = request.env['attendance.claim.approval'].create({
                'employee_id': employee_id.id,
                'manager_id': employee_id.parent_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'index': index,
                'request_hour': time_float,
                'approved_hour': time_float,
                'reason': post.get('reason')
            })
            template = request.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_claim_alert')
            template.send_mail(approval_id.id, force_send=True)
            return request.render(
                "tg_attendance.attendance_claim_view_from_confirm_view",
                {'show_form': True, 'reference': approval_id, 'show_reclaim': approval_id.show_reclaim})

    @route('/submit/claim/attendance', auth='user', website=True)
    def create_attendance_request(self, **post):
        if post.get('date_from') and post.get('date_to') and post.get('employee_id'):
            date_from = datetime.strptime(post.get('date_from'), '%Y-%m-%d %H:%M:%S') - timedelta(hours=5.5)
            date_to = datetime.strptime(post.get('date_to'), '%Y-%m-%d %H:%M:%S') - timedelta(hours=5.5)
            employee_id = request.env['hr.employee'].sudo().browse(
                int(post.get('employee_id')))

            approval_id = request.env['attendance.claim.approval'].search([
                ('employee_id', '=', employee_id.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to)
            ])
            if approval_id:
                return request.render(
                    "tg_attendance.attendance_claim_view_from_confirm_view",
                    {'reference': approval_id, 'show_reclaim': approval_id.show_reclaim, 'show_form': False})
            index = int(post.get('index'))
            hours = int(post.get('request_hour', 0))
            minutes = int(post.get('request_minutes', 0))
            time_float = hours + (minutes / 60)
            approval_id = request.env['attendance.claim.approval'].create({
                'employee_id': employee_id.id,
                'manager_id': employee_id.parent_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'index': index,
                'request_hour': time_float,
                'approved_hour': time_float,
                'reason': post.get('reason')
            })
            template = request.env.ref(
                'tg_attendance.email_template_employee_daily_attendance_claim_alert')
            template.send_mail(approval_id.id, force_send=True)
            return request.render(
                "tg_attendance.attendance_claim_view_from_confirm_view", {'show_form': True, 'reference': approval_id, 'show_reclaim': approval_id.show_reclaim})
    

    @route('/attendance/reclaim/form', auth='user', website=True)
    def reclaim_attendance(self, **kwargs):
        if kwargs.get('request_id'):
            request_id = request.env['attendance.claim.approval'].search([('id', '=', int(kwargs.get('request_id')))])
            if request_id:
                float_hours = request_id.request_hour

                # Extract hours, minutes, and seconds
                hours = int(float_hours)  # Get the integer part for hours
                remaining_minutes = (float_hours - hours) * 60  # Get the fractional part and convert to minutes
                minutes = int(remaining_minutes)  # Get the integer part for minutes
                seconds = int((remaining_minutes - minutes) * 60)  # Get the remaining fractional part and convert to seconds

                return request.render('tg_attendance.attendance_reclaim_form', {
                    'request_id': request_id,
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds
                })
        return request.render('tg_attendance.attendance_reclaim_not_found')

    @route('/attendance/reclaim/form/submit', auth='user', website=True)
    def reclaim_attendance_submit(self, **post):
        if post.get('request_id') and post.get('reason'):
            request_id = request.env['attendance.claim.approval'].search(
                [('id', '=', int(post.get('request_id')))])
            if request_id:
                hours = int(post.get('request_hour', 0))
                minutes = int(post.get('request_minutes', 0))
                time_float = hours + (minutes / 60)
                request_id.write({
                    'request_hour': time_float,
                    'approved_hour': time_float,
                    'reason': post.get('reason'),
                    'state': 'draft',
                    'show_reclaim': False
                })
                return request.render(
                    "tg_attendance.attendance_claim_view_from_confirm_view",
                    {'reference': request_id,
                     'show_reclaim': request_id.show_reclaim,
                     'show_form': False})
        return request.render('tg_attendance.attendance_reclaim_not_found')
