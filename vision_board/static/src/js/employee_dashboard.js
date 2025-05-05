/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, onMounted, useState } from '@odoo/owl';

class EmployeeDashboard extends Component {
    setup() {
        const currentDate = new Date();
        this.state = useState({
            loading: true,
            error: null,
            activeTab: 'attendance',
            selectedMonth: currentDate.getMonth() + 1, // 1-12
            selectedYear: currentDate.getFullYear(),
            data: {
                employee_info: {
                    name: '',
                    image_1920: null,
                    job_title: '',
                    department: {
                        name: '',
                        manager: '',
                        member_count: 0
                    },
                    joining_date: '',
                    time_since_joining: {
                        years: 0,
                        months: 0
                    },
                    work_email: '',
                    mobile_phone: '',
                    work_location: '',
                    parent_id: '',
                    coach_id: ''
                },
                attendance: {
                    check_in: null,
                    check_out: null,
                    worked_hours: 0
                },
                leave: {
                    leaves: [],
                    approved_count: 0,
                    to_approve_count: 0
                },
                projects: []
            }
        });

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.action = useService('action');

        onMounted(() => {
            this.loadEmployeeData();
        });
    }

    async loadEmployeeData() {
        const currentDate = new Date();
        try {
            const data = await this.rpc('/vision_board/employee_data', {
                month: currentDate.getMonth() + 1,
                year: currentDate.getFullYear()
            });
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.data = data;
                // Update state with current date
                this.state.selectedMonth = currentDate.getMonth() + 1;
                this.state.selectedYear = currentDate.getFullYear();
            }
        } catch (error) {
            this.state.error = "Failed to load employee data.";
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    switchTab(tab) {
        this.state.activeTab = tab;
    }

    async viewProject(projectId) {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'project.project',
            res_id: projectId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    getMonthOptions() {
        return [
            { value: 1, label: 'January' },
            { value: 2, label: 'February' },
            { value: 3, label: 'March' },
            { value: 4, label: 'April' },
            { value: 5, label: 'May' },
            { value: 6, label: 'June' },
            { value: 7, label: 'July' },
            { value: 8, label: 'August' },
            { value: 9, label: 'September' },
            { value: 10, label: 'October' },
            { value: 11, label: 'November' },
            { value: 12, label: 'December' }
        ];
    }

    getYearOptions() {
        const currentYear = new Date().getFullYear();
        const years = [];
        for (let year = currentYear - 2; year <= currentYear + 2; year++) {
            years.push({ value: year, label: year.toString() });
        }
        return years;
    }

    async onDateChange() {
        // Store current selections
        const selectedMonth = this.state.selectedMonth;
        const selectedYear = this.state.selectedYear;
        
        this.state.loading = true;
        try {
            const data = await this.rpc('/vision_board/employee_data', {
                month: selectedMonth,
                year: selectedYear
            });
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.data = data;
                // Ensure selections are preserved
                this.state.selectedMonth = selectedMonth;
                this.state.selectedYear = selectedYear;
            }
        } catch (error) {
            this.state.error = "Failed to load employee data.";
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }
}

EmployeeDashboard.template = 'EmployeeDashboard';
EmployeeDashboard.props = {
    action: { type: Object, optional: true },
    actionId: { type: Number, optional: true },
    className: { type: String, optional: true },
};

registry.category('actions').add('vision_board.employee_dashboard', EmployeeDashboard);

export default EmployeeDashboard;