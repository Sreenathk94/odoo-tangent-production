/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { session } from "@web/session";

// Helper function to extract name from Odoo many2one field
const getFieldName = (field) => Array.isArray(field) ? field[1] || "-" : "-";

export class LateCheckinDashboard extends Component {
    static template = "employee_late_checkin.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            records: [],
            showFilterDropdown: false,
            selectedFilter: "latest",
            showDateInputs: false,
            startDate: "",
            endDate: "",
        });

        // Bind event handlers
        this.toggleFilterDropdown = this.toggleFilterDropdown.bind(this);
        this.applyFilter = this.applyFilter.bind(this);
        this.onDateChange = this.onDateChange.bind(this);
        this.clearRecords = this.clearRecords.bind(this);
        this.downloadPDF = this.downloadPDF.bind(this);

        onWillStart(async () => {
            try {
                await Promise.all([
                    loadJS("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"),
                    loadJS("https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"),
                ]);
            } catch (error) {
                console.error("Error loading jsPDF libraries:", error);
                this.notification.add("Failed to load PDF generation libraries.", { type: "danger" });
                return;
            }
            await this.fetchLateCheckinRecords();
        });
    }

    // Calculate taxes for a POS order amount (18% IGST or 9% CGST + 9% SGST)
    calculatePosOrderTaxes(amount, useIGST = false) {
        if (useIGST) {
            const igst = amount * 0.18;
            return { igst, cgst: 0, sgst: 0, total: amount + igst };
        } else {
            const cgst = amount * 0.09;
            const sgst = amount * 0.09;
            return { igst: 0, cgst, sgst, total: amount + cgst + sgst };
        }
    }

    toggleFilterDropdown() {
        this.state.showFilterDropdown = !this.state.showFilterDropdown;
    }

    async applyFilter(filter) {
        this.state.selectedFilter = filter;
        this.state.showFilterDropdown = false;
        this.state.showDateInputs = filter === "custom";
        await this.fetchLateCheckinRecords();
    }

    async onDateChange() {
        if (this.state.startDate && this.state.endDate) {
            if (new Date(this.state.startDate) > new Date(this.state.endDate)) {
                this.notification.add("Start date cannot be after end date.", { type: "danger" });
                return;
            }
            await this.fetchLateCheckinRecords();
        }
    }

    async fetchLateCheckinRecords() {
        try {
            let domain = [];
            const today = new Date();
            const userTimezone = session.user_context.tz || "UTC";

            if (this.state.selectedFilter === "latest") {
                const yesterday = new Date(today);
                yesterday.setDate(today.getDate() - 1);
                const yesterdayStr = yesterday.toISOString().split("T")[0];
                domain = [
                    ["check_in", ">=", `${yesterdayStr} 00:00:00`],
                    ["check_in", "<=", `${yesterdayStr} 23:59:59`],
                ];
            } else if (this.state.selectedFilter === "this_week") {
                const firstDay = new Date(today);
                firstDay.setDate(today.getDate() - today.getDay());
                const firstDayStr = firstDay.toISOString().split("T")[0];
                domain = [["check_in", ">=", `${firstDayStr} 00:00:00`]];
            } else if (this.state.selectedFilter === "this_month") {
                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                const firstDayStr = firstDay.toISOString().split("T")[0];
                const lastDayStr = lastDay.toISOString().split("T")[0];
                domain = [
                    ["check_in", ">=", `${firstDayStr} 00:00:00`],
                    ["check_in", "<=", `${lastDayStr} 23:59:59`],
                ];
            } else if (this.state.selectedFilter === "custom" && this.state.startDate && this.state.endDate) {
                domain = [
                    ["check_in", ">=", `${this.state.startDate} 00:00:00`],
                    ["check_in", "<=", `${this.state.endDate} 23:59:59`],
                ];
            } else {
                return;
            }

            const records = await this.orm.searchRead(
                "hr.attendance",
                domain,
                ["id", "employee_id", "department_id", "check_in"],
                { order: "check_in desc" }
            );

            this.state.records = records.map((record) => {
                // Parse check_in directly as UTC
                const checkInDateTime = new Date(record.check_in + "Z"); // Append 'Z' to treat as UTC
                const actualCheckInTime = this.getActualCheckInTime(checkInDateTime);
                const delayedTime = this.calculateDelayedMinutes(checkInDateTime, actualCheckInTime);

                // Format date and time in user's timezone
                const formatter = new Intl.DateTimeFormat("en-CA", {
                    timeZone: userTimezone,
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                });
                const timeFormatter = new Intl.DateTimeFormat("en-US", {
                    timeZone: userTimezone,
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                });

                const formattedDate = formatter.format(checkInDateTime);
                const formattedTime = timeFormatter.format(checkInDateTime);

                return {
                    id: record.id,
                    employee_name: getFieldName(record.employee_id),
                    department: getFieldName(record.department_id),
                    date: formattedDate,
                    check_in_time: formattedTime,
                    delayed_minutes: delayedTime,
                };
            });
        } catch (error) {
            console.error("Error fetching late check-in records:", error);
            this.notification.add("Failed to fetch late check-in records.", { type: "danger" });
        }
    }

    getActualCheckInTime(checkInDate) {
        const actualCheckIn = new Date(checkInDate);
        actualCheckIn.setUTCHours(8, 15, 0, 0); // Set to 8:15 AM UTC
        return actualCheckIn;
    }

    calculateDelayedMinutes(checkInDateTime, actualCheckInTime) {
        const diffMs = checkInDateTime - actualCheckInTime;
        if (diffMs <= 0) return "00:00";
        const totalMinutes = Math.round(diffMs / (1000 * 60));
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
    }

    clearRecords() {
        this.state.records = [];
        this.state.selectedFilter = "latest";
        this.state.showDateInputs = false;
        this.state.startDate = "";
        this.state.endDate = "";
    }

    downloadPDF() {
        if (!window.jspdf) {
            this.notification.add("PDF library not loaded.", { type: "danger" });
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        doc.setFontSize(16);
        doc.text("Late Check-in Records", 20, 20);

        const headers = ["S.No", "ID", "Employee", "Department", "Date", "Check-in Time", "Delayed (HH:mm)"];
        const data = this.state.records.map((record, index) => [
            (index + 1).toString(),
            record.id,
            record.employee_name,
            record.department,
            record.date,
            record.check_in_time,
            record.delayed_minutes,
        ]);

        doc.autoTable({
            head: [headers],
            body: data,
            startY: 30,
            theme: "grid",
            styles: { fontSize: 10 },
            headStyles: { fillColor: [0, 102, 204] },
            margin: { top: 30 },
        });

        doc.save("late_checkin_records.pdf");
    }
}

registry.category("actions").add("late_checkin_dashboard", LateCheckinDashboard);