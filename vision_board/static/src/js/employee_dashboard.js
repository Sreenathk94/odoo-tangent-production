/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, onMounted, useState,onWillStart } from '@odoo/owl';
import {loadJS} from "@web/core/assets";

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
        this.leaveChart = null;

        onWillStart(async () => {
            await loadJS('https://cdn.jsdelivr.net/npm/chart.js');
        });

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
                // Initialize leave chart after data is loaded
                this.initializeLeaveChart();
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
        if (tab === 'leave' && this.state.data.leave) {
            // Initialize chart when switching to leave tab
            setTimeout(() => {
                this.initializeLeaveChart();
            }, 100);
        }
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

    initializeLeaveChart() {
        console.log("initializeLeaveChart");
        const ctx = document.getElementById('leaveChart');
        if (!ctx) {
            console.log("Canvas element not found");
            return;
        }

        if (this.leaveChart) {
            this.leaveChart.destroy();
        }

        // Prepare chart data from leaves
        const leaves = this.state.data.leave.leaves;
        if (!leaves || leaves.length === 0) {
            console.log("No leave data available");
            return;
        }

        console.log("Leave data:", leaves);
        
        // Get all months for x-axis
        const months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        // Create datasets for each leave type
        const datasets = leaves.map((leave, index) => ({
            label: leave.name,
            data: leave.monthly_data || Array(12).fill(0), // Use actual monthly data or zeros if not available
            backgroundColor: this.getRandomColor(index),
            borderColor: this.getRandomColor(index),
            borderWidth: 1
        }));

        this.leaveChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Months'
                        }
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Days Taken'
                        },
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw} days`;
                            }
                        }
                    },
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Leave Distribution by Month and Type'
                    }
                }
            }
        });
    }

    getRandomColor(index) {
        const colors = [
            'rgba(255, 99, 132, 0.7)',
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(199, 199, 199, 0.7)',
            'rgba(83, 102, 255, 0.7)',
            'rgba(40, 159, 64, 0.7)',
            'rgba(210, 199, 199, 0.7)'
        ];
        return colors[index % colors.length];
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