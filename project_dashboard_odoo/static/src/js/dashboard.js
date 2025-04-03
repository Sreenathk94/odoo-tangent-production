/** @odoo-module */
import {registry} from '@web/core/registry';
import {useService} from "@web/core/utils/hooks";

const {Component, useState, onMounted} = owl;
import {jsonrpc} from "@web/core/network/rpc_service";

export class ProjectDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            total_projects: 0,
            active_projects: 0,
            completed_projects: 0,
            projects: [],
            project_stages: [],
            filter_status: "",
            filter_date: ""
        });
        onMounted(() => {
            this.fetchStages()
            this.fetchProjects()
        })
    }

    async fetchStages() {
        const project_stages = await this.orm.searchRead("hr.timesheet.status", [], ["name", "id"])
        this.state.project_stages = project_stages
        console.log(project_stages, "project_stages")
    }


    async fetchProjects() {
        const domain = [];
        if (this.state.filter_status) domain.push(['status', '=', this.state.filter_status]);
        this.orm.searchRead("project.project", domain, ["name", "id", "timesheet_status_id", "timesheet_duration"]).then((result) => {
            this.state.projects = result.map(project => {
                // Ensure timesheet_duration is a number before processing
                const totalMinutes = project.timesheet_duration ? Math.round(project.timesheet_duration * 60) : 0;
                const hours = Math.floor(totalMinutes / 60);
                const minutes = totalMinutes % 60;

                return {
                    id: project.id,
                    name: project.name,
                    status: project.timesheet_status_id?.[1] || "No Status Assigned",
                    timesheet_duration: `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`, // Format as HH:MM
                };

            });

            this.state.total_projects = result.length;
            this.state.active_projects = this.state.projects.filter(p => p.status === "Active").length;
            this.state.completed_projects = this.state.projects.filter(p => p.status === "Completed").length;
            this.updateProjectTimeChart();
            this.updateProjectStatusChart()
        });
    }

updateProjectStatusChart() {
    const ctx = document.getElementById('projectStatusChart').getContext('2d');

    // Destroy existing chart if it exists
    if (this.chartInstance1) this.chartInstance1.destroy();

    // Prepare data: Count projects per stage
    const stageLabels = this.state.project_stages.map(stage => stage.name);
    const stageCounts = stageLabels.map(stageName =>
        this.state.projects.filter(p => p.status === stageName).length
    );

    // Count projects without an assigned stage
    const notAssignedCount = this.state.projects.filter(p => p.status === "No Status Assigned").length;
    if (notAssignedCount > 0) {
        stageLabels.push("Not Assigned");
        stageCounts.push(notAssignedCount);
    }

    // Define colors
    const barColors = ["#007bff", "#17a2b8", "#28a745", "#ffc107", "#dc3545", "#6610f2", "#fd7e14"];
    const backgroundColors = stageLabels.map((_, index) => barColors[index % barColors.length]);

    // Create the Bar Chart
    this.chartInstance1 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: stageLabels,
            datasets: [{
                label: 'Number of Projects',
                data: stageCounts,
                backgroundColor: backgroundColors,
                borderColor: backgroundColors.map(color => color.replace("1)", "0.8)")),
                borderWidth: 1,
                barThickness: 40,
                hoverBackgroundColor: backgroundColors.map(color => color + "cc")
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 14, weight: "bold" }, color: "#333" }
                },
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, font: { size: 14 }, color: "#333" },
                    grid: { color: "rgba(200, 200, 200, 0.3)" }
                }
            },
            plugins: {
                tooltip: {
                    backgroundColor: "rgba(0,0,0,0.7)",
                    titleFont: { size: 16, weight: "bold" },
                    bodyFont: { size: 14 },
                    padding: 10
                },
                legend: { display: false }
            },
            animation: {
                duration: 1000,
                easing: "easeOutBounce"
            }
        }
    });
}

updateProjectTimeChart() {
    const ctx = document.getElementById('projectTimeChart').getContext('2d');

    // Destroy existing chart if it exists
    if (this.chartInstance2) this.chartInstance2.destroy();

    // Truncate project names (max 15 chars)
    const projectNames = this.state.projects.map(p =>
        p.name.length > 15 ? p.name.substring(0, 15) + "..." : p.name
    );

    // Convert HH:MM to total hours
    const timeDurations = this.state.projects.map(p => {
        const [hours, minutes] = p.timesheet_duration.split(":").map(Number);
        return hours + minutes / 60; // Convert to decimal
    });

    // Create the Horizontal Bar Chart
    this.chartInstance2 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: projectNames,
            datasets: [{
                label: 'Time Spent (Hours)',
                data: timeDurations,
                backgroundColor: "#ff6384",
                borderColor: "#c0392b",
                borderWidth: 1,
                hoverBackgroundColor: "#ff6384cc"
            }]
        },
        options: {
            indexAxis: 'y', // Make it a horizontal bar chart
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 14 }, color: "#333" }
                },
                y: {
                    grid: { color: "rgba(200, 200, 200, 0.3)" },
                    ticks: { font: { size: 14, weight: "bold" }, color: "#333" }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            const index = tooltipItem.dataIndex;
                            const fullName = this.state.projects[index].name; // Show full name in tooltip
                            const value = tooltipItem.raw;
                            const hours = Math.floor(value);
                            const minutes = Math.round((value - hours) * 60);
                            return `${fullName}: ${hours}:${minutes.toString().padStart(2, '0')} Hours`;
                        }.bind(this) // Bind `this` to access `state.projects`
                    }
                }
            }
        }
    });
}

    applyFilters() {
        this.fetchProjects();
    }
}

ProjectDashboard.template = "ProjectDashboard";
registry.category("actions").add("project_dashboard", ProjectDashboard);