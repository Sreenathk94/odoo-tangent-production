/** @odoo-module */
import {registry} from "@web/core/registry";
import {Component, useState} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {jsonrpc} from "@web/core/network/rpc_service";

class CustomHrAttendanceReport extends Component {
    static template = "attendence_work_report.custom_hr_attendance_report";
    static components = {Dropdown, DropdownItem};

    setup() {
        this.state = useState({
            filterWise: [
                {label: "Today", value: "today"},
                {label: "This Week", value: "week"},
                {label: "This Month", value: "month"},
                {label: "By Custom", value: "custom"}
            ],
            totalPositiveCost: false,
            totalNegativeCost: false,
            filteredRecords: [],
            filterLabel: "",
            selectedFilter: '',
            customStartDate: null,
            customEndDate: null,
        });
    }

    async onFilterSelected(filterValue, filterLabel) {
        this.state.filterLabel = filterLabel;
        this.state.selectedFilter = filterValue;
        console.log("filterValue", this.state.selectedFilter != 'custom')
            this.state.customStartDate = false;
            this.state.customEndDate = false;

        if (this.state.selectedFilter != 'custom') {

            console.log("getttttttt")
            var data = await jsonrpc('/custom_hr_attendance/get_filtered_attendance', {
                "filterValue": this.state.selectedFilter,
                "start_date": false,
                "end_date":false
            });
            this.state.totalPositiveCost = data.total_positive_cost || 0;
            this.state.totalNegativeCost = data.total_negative_cost || 0;
            this.state.filteredRecords = data.records || [];
        }
        // var data = await jsonrpc('/custom_hr_attendance/get_filtered_attendance', {
        //     filterValue,
        //     "start_date": this.state.customStartDate,
        //     "end_date": this.state.customEndDate
        // });


        console.log(data)

        console.log("SDatta", this.state.totalPositiveCost)
        console.log("SDatta", this.state.totalNegativeCost)
    }

    async confirmCustomDate() {
        console.log("confirmCustomDate")
        console.log(this.state.customStartDate)
        console.log(this.state.customEndDate)
        if (!this.state.customStartDate || !this.state.customEndDate) {
            return
        } else {
            var data = await jsonrpc('/custom_hr_attendance/get_filtered_attendance', {
                "filterValue": this.state.selectedFilter,
                "start_date": this.state.customStartDate,
                "end_date": this.state.customEndDate
            });
            console.log("Dataaa", data)
            this.state.totalPositiveCost = data.total_positive_cost || 0;
            this.state.totalNegativeCost = data.total_negative_cost || 0;
            this.state.filteredRecords = data.records || [];
        }
    }
}

registry.category("actions").add("custom_hr_attendance_action", CustomHrAttendanceReport);
