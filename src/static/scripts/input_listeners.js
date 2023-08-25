let addressField = $('#walletAddress')
let button = $('#receiveButton')
let addrText = $('.addressFeedback')
let addrIcon = $('.addressIcon')
let checkbox = $('#walletSyncedCheck')

addressField.on('input', async function() {updateAddress()});
checkbox.on('input', async function() {updateAddress()})

let isClaimed = document.cookie.match('claimed')

if (isClaimed) {
    button.text("CLAIMED")
    addressField.attr('disabled', true)
}

function updateAddress() {
    if (!addressField.val()) {
        addrIcon.css('color', 'grey')
        button.attr('disabled', true)
        addrText.text('')
    } else {
        if (addressField.val().trim().split('@')[0].length === 52
                && addressField.val().includes("@epicbox")) {
            addrIcon.css('color', 'green')
            addrText.text('')

            if (checkbox.is(':checked')) {
                button.attr('disabled', false)
            }
        } else {
            addrIcon.css('color', 'orange')
            button.attr('disabled', true)
            addrText.text(`* Invalid wallet address`)
        }
    }
}

 $('.panel-collapse').on('show.bs.collapse', function () {
    $(this).siblings('.panel-heading').addClass('active');
  });

  $('.panel-collapse').on('hide.bs.collapse', function () {
    $(this).siblings('.panel-heading').removeClass('active');
  });