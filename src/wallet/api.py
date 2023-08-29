import json

from django.http import HttpResponse
from grpclib.client import Channel
import psutil
import ninja

from wallet.python_sdk.src.grpc_server import server_pb2, server_grpc
from wallet.schema import Payload, TxSchema, BalanceSchema
from wallet.python_sdk.src.wallet import models
from wallet.python_sdk.src import utils
from wallet.models import FaucetWallet
from core import envs
from faucet.models import (
    Transaction as TransactionManager,
    connection_details,
    connection_authorized,
    update_connection_details
    )


SUCCESS = False
ERROR = True

api = ninja.NinjaAPI(docs_url=None)
active_listeners: dict[psutil.Process: models.Listener] = dict()


async def wallet_call(call: str, data: dict = None) -> str:
    async with Channel(envs.GRPC_HOST, envs.GRPC_PORT) as channel:
        if data is None: data = dict()
        server = server_grpc.WalletServerStub(channel)
        kwargs = {'call': call, 'data': json.dumps(data)}
        reply = await server.Call(server_pb2.WalletRequest(**kwargs))
        return reply.result


@api.post('/claim')
async def claim(request, response: HttpResponse, payload: Payload):
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

    # Send the transaction
    tx_slate = await wallet_call(call='send_epicbox', data=tx_args)
    tx_slate = json.loads(tx_slate)

    if tx_slate['error']:
        if 'NotEnoughFunds' in tx_slate['msg']:
            return utils.response(ERROR, f'Not enough funds in the wallet')
        else:
            return utils.response(ERROR, tx_slate['msg'])

    # Save transaction details to the database
    wallet_instance = await FaucetWallet.objects.aget(name=envs.WALLET['NAME'])
    transaction = await TransactionManager.create_faucet_transaction(address=tx_args['address'], slate=tx_slate['data'], wallet=wallet_instance)

    # if 'PRODUCTION' in os.environ and address.address not in envs.DEV_ADDRESSES:
    # Update user's activity
    await update_connection_details(ip.address, address.address)

    return utils.response(SUCCESS, transaction.status, str(transaction.tx_slate_id))


@api.get('/balance')
async def wallet(request):
    balance = await wallet_call(call='balance')
    return json.loads(balance)


@api.get('/outputs')
async def create_outputs(request, outputs: int = 15):
    response = await wallet_call(call='create_outputs', data={'num': outputs})
    return {'action': 'create_outputs', 'data': response}


@api.post('/update_tx')
async def update_tx(request, tx: TxSchema):
    await TransactionManager.updater_callback(tx.data)
    return {'action': 'update_tx', 'data': tx.data}


@api.post('/update_balance')
async def update_balance(request, balance: BalanceSchema):
    wallet_instance = await FaucetWallet.objects.aget(name=envs.WALLET['NAME'])
    wallet_instance.balance = json.loads(balance.data)
    await wallet_instance.asave()
    return {'action': 'update_balance', 'data': balance.data}