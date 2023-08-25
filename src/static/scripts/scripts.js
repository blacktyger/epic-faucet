let feedbackField = $('.feedbackField')
let confirmButton = $('#receiveButton')
let addressIcon = $('.addressIcon')
let address = $('#walletAddress')

const spinnerHTMLsm = `<div class="spinner-border spinner-border-sm fs-6" role="status"></div>`
const spinnerHTML = `<div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>
                     <div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>
                     <div class="spinner-grow spinner-grow-sm align-middle" role="status"></div>`

// PROCESS USER REQUEST
async function requestTransaction(code) {
    let taskFinished = false
    let query = "http://localhost:8000/api/wallet/initialize_transaction"
    let body = {
        receiver_address: address.val(),
        code: code,
        data: {}
    }
    console.log(body)
    toast = spawnToast('info', `${spinnerHTMLsm} Preparing your transaction..`)
    updateForm(spinnerHTML)
    feedbackField.text('Connecting to the server..')

    let response = await fetch(query, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': "*",
            'Access-Control-Allow-Headers': "Origin, X-Requested-With, Content-Type, Accept"
        },
        body: JSON.stringify(body),
      }).then(checkStatus)
        // .then(r => r)
        .catch(err => console.log(err))

    if (response) {
        if (!response.error && 'result' in response) {
            feedbackField.text('Preparing wallet..')

            let taskId = response.result.task_id
            let task = await getTaskStatus(taskId)

            while (!taskFinished) {
                if (task.status === 'finished') {
                    feedbackField.text('')
                    taskFinished = true
                    console.log(task)
                    if (task.result.error) {
                        transactionFailedAlert()
                    } else {
                        await spawnToast('success', 'Transaction sent successfully!', 3500)
                        resetForm()
                        location.reload()
                    }

                } else if (task.status === 'failed') {
                    feedbackField.text('')
                    taskFinished = true
                    transactionFailedAlert()
                    console.log(task.status)

                } else if (task.status === 'queued') {
                    console.log(task.status)
                    await sleep(2000)
                    feedbackField.text('Preparing wallet..')
                    task = await getTaskStatus(taskId)

                } else if (task.status === 'started') {
                    console.log(task.status)
                    await sleep(2000)
                    feedbackField.text('Preparing transaction..')
                    task = await getTaskStatus(taskId)
                }
            }
        } else {
            userRestrictedAlert(response.message)
            feedbackField.text('')
            await resetForm()
        }
    }
    feedbackField.text('')
}


// RESTRICTED USER ALERT
function userRestrictedAlert(result) {
        Swal.fire({
        icon: 'info',
        // title: `UNSUCCESSFUL`,
        html:`
            ${result}
            <hr class="mt-5" />
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
    }).then((result) => {console.log('alert result:', result)})
}


async function transactionInitializedAlert(task) {
    // SweetAlert2 instance spawned when first step of the transaction was successful
    // and script is waiting for receiving wallet to send response slate.
    let timerInterval

    Swal.fire({
        html:
            `<div class="card mt-1 bg-blue text-light">
                 <div class="card-img">
                    <img class="card-img" src="receiving_tx.png" alt="img">
                 </div>
                 <div class="card-body">
                     Keep your wallet open until you can see an incoming transaction.
                     <a href="#" data-bs-toggle="tooltip" data-bs-title="
                        If it won't appear after few minutes you may need to refresh (drag down) the wallet.">
                        <b><sup><i class="fa-solid fa-circle-info text-light"></i></sup></b>
                     </a>
                     If the transaction did not appear, or it is not displayed as 
                     <span class="text-success"></span> 'Received'</span>
                     after 10 minutes please use the <span class="text-danger">NOT RECEIVED</span> button.
                     <br><br>
<!--                     <p>After <span><b>180</b></span> seconds transaction will be automatically cancelled.</p>-->
                 </div>
                 <div class="card-footer mb-0 pb-0">
                     <small class="text-light-50"><pre>ID: ${task.result.result['tx_slate_id']}</pre></small>
                 </div>
             </div>`,
        timer: 1000*60*3,
        position: 'center',
        timerProgressBar: true,
        showCancelButton: true,
        cancelButtonText: `<i class="fa fa-xmark"></i> NOT RECEIVED`,
        allowOutsideClick: false,
        cancelButtonColor: 'orange',
        showConfirmButton: true,
        confirmButtonText: `<i class="fa fa-check"></i> RECEIVED`,
        confirmButtonColor: 'green',

        didOpen: () => {
            getToolTips()
            const b = Swal.getHtmlContainer().querySelector('span').querySelector('b')
            timerInterval = setInterval(() => {
                b.textContent = (Swal.getTimerLeft() / 1000).round(0)
            }, 1000)
        },
        willClose: () => {clearInterval(timerInterval)}

    }).then(async (aResult) => {
        let tResult = task.result.result
        console.log(await aResult)
        console.log(tResult)
        updateForm(spinnerHTMLsm)

        // Closed by timer
        if (aResult.dismiss === Swal.DismissReason.timer) {
            console.log('Closed by timer')
            await cancelTransaction(tResult['tx_slate_id'])
            await spawnToast('error', 'Transaction time expired')

        // Canceled by user
        } else if (aResult.dismiss === Swal.DismissReason.cancel) {
            console.log('Canceled by user')
            await cancelTransaction(tResult['tx_slate_id'])
            await spawnToast('warning', 'Transaction cancelled by user.')
            await resetForm()

        // Confirmed by user
        } else if (aResult.isConfirmed) {
            updateForm(spinnerHTML)
            feedbackField.text('Waiting for response..')

            let taskFinished = false
            console.log('Confirmed by user')
            let result = await finalizeTransaction(tResult['tx_slate_id'])
            console.log(result)
            let task = await getTaskStatus(result.result['task_id'])
            console.log(task)

            while (!taskFinished) {
                if (task.status === 'finished') {
                    feedbackField.text('')
                    taskFinished = true
                    await finishedTaskHandler(task, 'confirmed')
                } else if (task.status === 'failed') {
                    feedbackField.text('')
                    taskFinished = true
                    console.log('failed' + task.result)
                    await cancelTransaction(tResult['tx_slate_id'])
                    transactionFailedAlert("Receiver wallet was offline, transaction is cancelled.")
                } else {
                    console.log(task.status)
                    await sleep(2000)
                    task = await getTaskStatus(result.result['task_id'])
                }
            }
        }
    })
}


// CONFIRMED TRANSACTION ALERT
function transactionConfirmedAlert() {
    Swal.fire({
        icon: 'success',
        title: `Transaction confirmed!`,
        html:`Your EPIC will be spendable after <b>1 confirmation</b>, on average ~<b>1 minute</b>.`,
        position: 'center',
        showConfirmButton: true,
        confirmButtonText: `<i class="fa fa-check"></i> OK`,
    }).then(async (result) => {
        await resetForm()
        console.log('alert result:', result)
    })
}


// FAILED TRANSACTION ALERT
function transactionFailedAlert() {
        Swal.fire({
        icon: 'warning',
        title: `UNSUCCESSFUL`,
        html:`
             There was a problem with your transaction, you can try again or contact our support
             via Telegram messenger.
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
    }).then(async (result) => {
        await resetForm()
        console.log('alert result:', result)
    })
}


// HANDLE FINISHED TASK
async function finishedTaskHandler(task, type) {
    console.log(task.result);
    if (!task.result) {
        console.log('error: task finished but no results');
    } else if (task.result.error) {
        if (type === 'confirmed') {
            await transactionFailedAlert(task.result.message)
        } else if (type === 'sent') {
            await transactionFailedAlert(task.result.message)
        }
    } else {
        if (type === 'confirmed') {
            await transactionConfirmedAlert()
        } else if (type === 'sent') {
            await transactionInitializedAlert(task)
        }
    }
}


// SPAWN TOAST NOTIFICATION
async function spawnToast(icon, title, time=0) {
    const Toast = Swal.mixin({
        toast: true,
        position: 'center',
        iconColor: 'white',
        customClass: {
            popup: 'colored-toast'
        },
        showConfirmButton: false,
        timer: time,
        timerProgressBar: true
    })
    let toast = await Toast.fire({
        icon: icon,
        title: title,
    })

    return toast
}


// GET TASK STATUS FROM REDIS/QUEUE
async function getTaskStatus(taskId) {
    let query = `http://localhost:8000/api/wallet/get_task/id=${taskId}`

    return await fetch(query, {
        method: 'GET',
        headers: {
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
      .catch(err => {console.log(err)})
}


// FINALIZE TRANSACTION
function finalizeTransaction(tx_slate_id) {
    let query = `/api/finalize_transaction/tx_slate_id=${tx_slate_id}&address=${address.val()}`

    return fetch(query, {
        method: 'GET',
        headers: {
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
      .catch(err => {console.log(err)})
}


// CANCEL TRANSACTION
function cancelTransaction(tx_slate_id) {
    let query = `/api/cancel_transaction/tx_slate_id=${tx_slate_id}&address=${address.val()}`

    return fetch(query, {
        method: 'GET',
        headers: {
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
      .catch(err => {console.log(err)})
}


// FEEDBACK IF CONNECTION WITH DB FAILED
checkStatus = async (response) => {
    if (response.status >= 200 && response.status < 300)
        return await response.json()
    feedbackField.text(response.status)
}


// UPDATE ADDRESS INPUT AND CONFIRM BUTTON STATE
function updateForm(conf_btn_html) {
    confirmButton.attr('disabled', true)
    confirmButton.html(conf_btn_html)
    addressIcon.css('color', 'grey');
    address.attr('disabled', true)
}


// RESET ADDRESS INPUT AND CONFIRM BUTTON STATE
async function resetForm() {
    confirmButton.html('CONFIRM')
    confirmButton.timedDisable(5);
    await sleep(5000)
    confirmButton.attr('disabled', false);
    addressIcon.css('color', 'green');
    address.attr('disabled', false);
}

function toast(text='', icon='info', timer=3000, timerProgressBar=false) {
    const Toast = Swal.mixin({
        toast: true,
        showConfirmButton: true,
        didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
        }
    });
    Toast.fire({
        icon: icon,
        text: text,
        timer: timer,
        timerProgressBar: timerProgressBar,
    });
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
};
