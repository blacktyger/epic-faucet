import subprocess
import asyncio
import time
import json

from grpclib.client import Channel
import uvicorn
import psutil

from wallet.python_sdk.src.grpc_server.server_grpc import WalletServerStub
from wallet.python_sdk.src.grpc_server.server_pb2 import WalletRequest, WalletResponse

from wallet.python_sdk.src import utils
from core import envs


grpc_server_path = "/home/blacktyger/epic-faucet/src/wallet/python_sdk/server.py"


async def run_wallet():
    async with Channel(envs.GRPC_HOST, envs.GRPC_PORT) as channel:
        wallet = WalletServerStub(channel)

        open_wallet = {'call': 'open', 'data': json.dumps({
                    'wallet_data_directory': '/home/blacktyger/python-sdk/tests/epic-wallet',
                    'balance_updater_interval': envs.BALANCE_UPDATER_INTERVAL,
                    'balance_updater_api_url': envs.BALANCE_UPDATER_API_URL,
                    'tx_updater_api_url': envs.TX_UPDATER_API_URL,
                    'long_running': True,
                    'epicbox': True,
                    'open': True,
                    })}

        await wallet.Call(WalletRequest(**open_wallet))


if __name__ == '__main__':
    subprocess.Popen(['python', grpc_server_path])
    time.sleep(2)
    asyncio.run(run_wallet())
    uvicorn.run("core.asgi:application", host=envs.UVICORN_HOST, port=envs.UVICORN_PORT, lifespan="off", workers=1)

    # close running processes
    owner_p = utils.find_process_by_port(envs.WALLET['OWNER_API_PORT'])
    if owner_p:
        utils.logger.debug(f">> KILLING {psutil.Process(owner_p)}")
        psutil.Process(owner_p).kill()

    epicbox_p = utils.find_process_by_name('epicbox')
    if epicbox_p:
        utils.logger.debug(f">> KILLING {psutil.Process(epicbox_p[0])}")
        psutil.Process(epicbox_p[0]).kill()

    grpc_p = utils.find_process_by_port(envs.GRPC_PORT)
    if grpc_p:
        utils.logger.debug(f">> KILLING {psutil.Process(grpc_p)}")
        psutil.Process(grpc_p).kill()