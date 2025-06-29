/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component, useState, onWillStart, useEffect, onMounted } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class LeaveTypeWidget extends Component {
    static template = "hr_leave_widget.LeaveTypeWidget";
    static components = { Many2OneField };
    static props = {
        ...Many2OneField.props,
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            leaveTypes: [],
        });

        onWillStart(async () => {
            try {
                await this.loadLeaveTypes();
            } catch (error) {
                console.error("Error loading leave types:", error);
                this.notification.add(
                    "Failed to load leave type selectability. Please try again.",
                    { type: "danger" }
                );
            }
        });

        onMounted(() => {
            this.updateSelectedStyle();
        });

        useEffect(() => {
            this.updateSelectedStyle();
        }, () => [this.state.leaveTypes, this.props.value]);
    }

    async loadLeaveTypes() {
        const employeeId = this.props.record.data.employee_id?.[0];
        if (!employeeId || this.props.name !== "holiday_status_id") {
            this.state.leaveTypes = [];
            return;
        }
        try {
            const result = await this.orm.call(
                "hr.leave",
                "get_leave_type_selectability",
                [employeeId],
                { context: this.props.record.context }
            );
            this.state.leaveTypes = result || [];
        } catch (error) {
            console.error("RPC error:", error);
            this.state.leaveTypes = [];
            throw error;
        }
    }

    updateDropdownStyles() {
        // Use document instead of this.el to account for dropdowns in portals
        const dropdown = document.querySelector(".o-autocomplete--dropdown-menu") || document.querySelector(".dropdown-menu");
        if (!dropdown) {
            return false;
        }
        const items = dropdown.querySelectorAll("li");
        items.forEach((item) => {
                const link = item.querySelector("a.dropdown-item"); // Target the <a> tag
                const text = link ? link.textContent.trim() : item.textContent.trim();
                const leaveType = this.state.leaveTypes.find((lt) => lt.name === text);
                if (leaveType && link) {
                    link.style.color = leaveType.selectable ? "green" : "red"; // Apply color to <a> tag
                    if (!leaveType.selectable) {
                        item.classList.add("o_non_selectable");
                        item.style.cursor = "not-allowed";
                        item.style.backgroundColor = "#ffe6e6";
                        link.style.color = "red";
                        item.title = "This leave type cannot be selected because the employee's visa expires within 6 months.";
                        link.addEventListener("click", (ev) => {
                            ev.preventDefault();
                            ev.stopPropagation();
                            this.notification.add(
                                "This leave type cannot be selected because the employee's visa expires within 6 months.",
                                { type: "warning" }
                            );
                        }, { once: true });
                    } else {
                        link.style.color = "green"; // Ensure selectable items are green
                    }
                }
            });
            return true;
    }

    updateSelectedStyle() {
        if (!this.el) {
            return;
        }
        const selected = this.el.querySelector(".o-autocomplete--input");
        if (selected && this.props.value) {
            const leaveType = this.state.leaveTypes.find((lt) => lt.id === this.props.value[0]);
            if (leaveType && !leaveType.selectable) {
                selected.style.color = "red";
                selected.title = "This leave type cannot be selected because the employee's visa expires within 6 months.";
            } else if (leaveType) {
                selected.style.color = "green";
                selected.title = "";
            } else {
                selected.style.color = "";
                selected.title = "";
            }
        }
    }

    onDropdownOpen() {
        // Retry until dropdown is found
        const tryUpdate = () => {
            const success = this.updateDropdownStyles();
            if (!success) {
                setTimeout(tryUpdate, 100); // Retry every 100ms until dropdown is found
            }
        };
        setTimeout(tryUpdate, 100); // Initial delay to allow dropdown rendering
    }

    async onInputClick() {
        try {
            await this.loadLeaveTypes();
            this.onDropdownOpen();
        } catch (error) {
            console.error("Error in onInputClick:", error);
            this.notification.add(
                "Failed to load leave type selectability. Please try again.",
                { type: "danger" }
            );
        }
    }
}

registry.category("fields").add("leave_type_widget", {
    component: LeaveTypeWidget,
    supportedTypes: ["many2one"],
    supportedOptions: many2OneField.supportedOptions,
    extractProps: many2OneField.extractProps,
});