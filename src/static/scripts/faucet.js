let receiveButton = $('#receiveButton')
let addressIcon = $('.addressIcon')
let address = $('#walletAddress')

let headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

const spinnerHTML = `<div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>
                            <div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>
                            <div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>`

async function claimCoins() {
    let query = "/wallet/claim"
    let body = {
        address: address.val(),
    }
    updateForm(spinnerHTML)

    spawnToast(icon='info', title='Preparing transaction..', timer=0, confBtn=false, position='center').catch()

    let response = await fetch(query, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body)
      }).catch(err => console.log(err))

    response = await response.json()
    console.log(response)

    if (response) {
        if (!response.error && 'result' in response) {
            updateForm('CLAIMED')
            spawnToast(icon='success', title='Transaction sent successfully', timer=3500, confBtn=false, position='center', timerProgressBar=true).catch()

        } else if (response.message) {
            resetForm().catch(err => console.log(err))
            failedTx(response.message)
        }
    }
}


// SPAWN TOAST NOTIFICATION
async function spawnToast(icon, title, timer=2500, confBtn=false,
                          position='top', timerProgressBar=false) {
    const Toast = Swal.mixin({
        toast: true,
        position: position,
        showConfirmButton: confBtn,
        timer: timer,
        timerProgressBar: timerProgressBar
    })
    toast = await Toast.fire({
        icon: icon,
        title: title,
    })
    return toast
}


function failedTx(message) {
    Swal.fire({
        icon: 'warning',
        title: `Transaction Failed`,
        html: `
         ${message}
         <hr class="mt-4" />
         <div class="my-2">
             Need support? Join
             <a href="https://t.me/GiverOfEpic" target="_blank" class="text-dark">
                 <i class="fa-brands fa-telegram ms-1"></i> <b>GiverOfEpic</b>. 
             </a>
         </div>
         <hr class="mb-2" />
         `,
        position: 'center',
        showConfirmButton: true,
        confirmButtonText: `<i class="fa fa-check"></i> CONFIRM`,
    })
}


// UPDATE ADDRESS INPUT AND CONFIRM BUTTON STATE
function updateForm(conf_btn_html) {
    receiveButton.attr('disabled', true)
    receiveButton.html(conf_btn_html)
    addressIcon.css('color', 'grey');
    address.attr('disabled', true)
}


// RESET ADDRESS INPUT AND CONFIRM BUTTON STATE
async function resetForm() {
    receiveButton.html('CLAIM')
    receiveButton.timedDisable(5);
    await sleep(5000)
    receiveButton.attr('disabled', false);
    addressIcon.css('color', 'green');
    address.attr('disabled', false);
}

// ROUND NUMBERS
Number.prototype.round = function(places) {
  return +(Math.round(this + "e+" + places)  + "e-" + places);
}


//TOOLTIP
$(document).ready(function(){
    getToolTips()
});
function getToolTips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
}


// SLEEP/WAIT FUNCTION
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


$.fn.timedDisable = function(time) {
    if (time == null) {time = 5}
    let seconds = Math.ceil(time); // Calculate the number of seconds

    return $(this).each(function() {
      const disabledElem = $(this);
      const originalText = this.innerHTML; // Remember the original text content

    // append the number of seconds to the text
    disabledElem.text(originalText + ' (' + seconds + ')');

    // do a set interval, using an interval of 1000 milliseconds
    //     and clear it after the number of seconds counts down to 0
      const interval = setInterval(function () {
          seconds = seconds - 1;
          // decrement the seconds and update the text
          disabledElem.text(originalText + ' (' + seconds + ')');
          if (seconds === 0) { // once seconds is 0...
              disabledElem.text(originalText); //reset to original text
              clearInterval(interval); // clear interval
          }
      }, 1000);
    });
}

