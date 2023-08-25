let timerInterval

function transactionStatusAlert() {
    Swal.fire({
        icon: 'success',
        title: 'Transaction sent!',
        html:
            `<p>Please refresh your mobile wallet and confirm incoming 
             transaction within next <strong></strong> minutes. 
             After that time transaction will be automatically cancelled.</p>` +
            `<p>You can safely close this window, or stay and check your transaction 
             status update.</p>` +
            `<hr><div class="fs-4 mb-2">TRANSACTION STATUS:</div>` +
            `<span class="status"></span> `,
            timer: 1000 * 60 * 60,
            didOpen: async () => {
                const content = Swal.getHtmlContainer()
                const $ = content.querySelector.bind(content)
                let responseReceived = false

                Swal.showLoading()
                timerInterval = setInterval(() => {
                    Swal.getHtmlContainer().querySelector('strong')
                        .textContent = (Swal.getTimerLeft() / (1000 * 60))
                        .toFixed(0)
                }, 100)

                while (!responseReceived) {
                    Swal.getHtmlContainer().querySelector('span')
                        .textContent = `⏳ Waiting for response..`
                    await sleep(2000)
                }
        },
        willClose: () => {
            clearInterval(timerInterval)
        }
    })
}