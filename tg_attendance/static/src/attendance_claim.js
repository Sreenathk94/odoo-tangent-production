/** @odoo-module **/


$('#attendance_claim_form').submit(function(ev){
    ev.preventDefault()
    if (parseFloat($('#request_hour').val()) > parseFloat($('#maximum_difference_in_minutes').data('minuts'))){
        alert('The requested time is greater than the actual claimable time.')
    }else{
        this.submit()
    }
})
