import threading

from django.http import HttpResponse
import psutil
import ninja

from core.envs import WALLET
from faucet.models import (
    Transaction as TransactionManager,
    connection_details,
    connection_authorized,
    update_connection_details
    )
from wallet.python_sdk import utils
from wallet.python_sdk.wallet import models
from wallet.models import FaucetWallet
from wallet.schema import Payload


SUCCESS = False
ERROR = True

# Get the FaucetWallet instance and run balance updater
try:
    instance_w, _ = FaucetWallet.objects.get_or_create(name=WALLET['NAME'])
    faucet_w = instance_w.get_wallet()

    t = threading.Thread(target=instance_w.updater, args=(30,), daemon=True)
    t.start()

except Exception as e:
    print(str(e))
    print(f">> NO WALLET INSTANCE")


api = ninja.NinjaAPI(docs_url=None)
active_listeners: dict[psutil.Process: models.Listener] = dict()


@api.post('/claim')
async def claim(request, response: HttpResponse, payload: Payload):
    # Check user cookie limit
    if request.COOKIES.get('claimed'):
        return utils.response(ERROR, 'already claimed')

    # Check user's limits
    ip, address = await connection_details(request, payload.address)
    authorized = await connection_authorized(ip, address)

    if authorized['error']:
        return authorized

    # Check daily transaction limits
    daily_limit = await TransactionManager.daily_limit()

    if daily_limit['error']:
        return daily_limit

    # Validate transaction args
    tx_args = {'amount': 0.01, 'address': payload.address}
    tx_args_validation = TransactionManager.validate_tx_args(**tx_args)

    if tx_args_validation['error']:
        return utils.response(ERROR, "Something went wrong, please try again later.")

    # Make sure epicbox listener is running
    epicbox_is_running = utils.find_process_by_name('epicbox')
    if not epicbox_is_running:
        print(">> EPICBOX_LISTENER wasn't running, starting..")
        await run_epicbox(request)

    # Send the transaction
    tx_slate = await faucet_w.send_epicbox_tx(**tx_args)

    if tx_slate['error']:
        if 'NotEnoughFunds' in tx_slate['msg']:
            return utils.response(ERROR, f'Not enough funds in the wallet')
        else:
            return utils.response(ERROR, tx_slate['msg'])

    # Save transaction details to the database
    transaction = await TransactionManager.create_faucet_transaction(address=tx_args['address'], slate=tx_slate['data'], wallet=faucet_w)

    # Update user's activity
    await update_connection_details(ip.address, address.address)

    # Set user cookie limit
    response.set_cookie("claimed", True, max_age=10)

    return utils.response(SUCCESS, transaction.status, str(transaction.tx_slate_id))


@api.get('/balance')
async def wallet(request):
    balance = await faucet_w.get_balance()
    return balance


@api.get('/run_epicbox')
async def run_epicbox(request):
    response = {
        'wallet': faucet_w.config.name,
        'action': 'run_epicbox',
        'data': {'address': faucet_w.config.epicbox_address}
        }
    # Set a callback function, it will listen for incoming transactions and update transaction status in the database
    callback = TransactionManager.updater_callback

    listener = await faucet_w.run_epicbox(logger=faucet_w.logger, callback=callback)
    active_listeners[listener.process] = listener
    response['data']['listener'] = str(listener)

    return response


@api.get('/stop_epicbox')
async def stop_epicbox(request):
    response = {'wallet': faucet_w.config.name, 'action': 'stop_epicbox', 'data': {}}

    for _, listener in active_listeners.items():
        response['data'][str(listener)] = 'stopped'
        listener.stop()

    return response
