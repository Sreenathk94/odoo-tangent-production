/** @odoo-module */
import {registry} from "@web/core/registry";
import {Component, useState, onWillStart, useEffect} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {jsonrpc} from "@web/core/network/rpc_service";
import {useService} from "@web/core/utils/hooks";

class CustomHrAttendanceReport extends Component {
    static template = "attendence_work_report.custom_hr_attendance_report";
    static components = {Dropdown, DropdownItem};

    setup() {
        this.orm = useService('orm');
        this.state = useState({
            filterWise: [
                {label: "Latest", value: "today"},
                {label: "This Week", value: "week"},
                {label: "This Month", value: "month"},
                {label: "By Custom", value: "custom"}
            ],
            totalPositiveCost: false,
            totalNegativeCost: false,
            filteredRecords: [],
            dateFilterAppliedRecords: [],
            filterLabel: "",
            selectedFilter: '',
            customStartDate: null,
            customEndDate: null,
            departmentFilter: null,
            depFilterLabel: false,
            selectedDepFilter: false
        });

        onWillStart(async () => {
            this.state.departmentFilter = await this.orm.searchRead('hr.department', [], ['name'])

        })
        useEffect(() => {
            this.applyFilter()
            this.recomputeTotalCost()
        }, () => [this.state.selectedDepFilter, this.state.dateFilterAppliedRecords])
    }

    async onFilterSelected(filterValue, filterLabel) {
        this.state.filterLabel = filterLabel;
        this.state.selectedFilter = filterValue;
        this.state.customStartDate = false;
        this.state.customEndDate = false;

        if (this.state.selectedFilter != 'custom') {

            var data = await jsonrpc('/custom_hr_attendance/get_filtered_attendance', {
                "filterValue": this.state.selectedFilter,
                "start_date": false,
                "end_date": false
            });
            this.state.dateFilterAppliedRecords = data.records || []
            this.state.totalPositiveCost = data.total_positive_cost || 0;
            this.state.totalNegativeCost = data.total_negative_cost || 0;
            this.state.filteredRecords = data.records || [];
        }



    }

    async confirmCustomDate() {
        if (!this.state.customStartDate || !this.state.customEndDate) {
            return
        } else {
            var data = await jsonrpc('/custom_hr_attendance/get_filtered_attendance', {
                "filterValue": this.state.selectedFilter,
                "start_date": this.state.customStartDate,
                "end_date": this.state.customEndDate
            });
            this.state.dateFilterAppliedRecords = data.records || []
            this.state.totalPositiveCost = data.total_positive_cost || 0;
            this.state.totalNegativeCost = data.total_negative_cost || 0;
            this.state.filteredRecords = data.records || [];
        }
    }

    DepartmentSelected(depId, depName) {
        this.state.depFilterLabel = depName
        this.state.selectedDepFilter = depId

    }

    applyFilter() {
        if (this.state.selectedDepFilter) {
            this.state.filteredRecords = this.state.dateFilterAppliedRecords.filter(rec => rec.department[1] == this.state.selectedDepFilter)
        } else {
            this.state.filteredRecords = this.state.dateFilterAppliedRecords
        }

    }

    recomputeTotalCost() {
        this.state.totalPositiveCost = this.state.filteredRecords.reduce((total, record) => total + record.positive_cost, 0)
        this.state.totalNegativeCost = this.state.filteredRecords.reduce((total, record) => total + record.negative_cost, 0)
    }
}

registry.category("actions").add("custom_hr_attendance_action", CustomHrAttendanceReport);
