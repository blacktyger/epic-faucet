import os
import subprocess
import asyncio
import time
import json

from grpclib.client import Channel
import uvicorn
import psutil

from wallet.python_sdk.src.grpc_server.server_grpc import WalletServerStub
from wallet.python_sdk.src.grpc_server.server_pb2 import WalletRequest

from wallet.python_sdk.src import utils
from core import envs


async def run_wallet():
    """ Init gRPC Client"""
    async with Channel(envs.GRPC_HOST, envs.GRPC_PORT) as channel:
        wallet = WalletServerStub(channel)

        open_wallet = {
            'call': 'open',
            'data': json.dumps({
                    'wallet_data_directory': envs.WALLET['WALLET_DIR'],
                    'balance_updater_interval': envs.BALANCE_UPDATER_INTERVAL,
                    'balance_updater_api_url': envs.BALANCE_UPDATER_API_URL,
                    'tx_cleaner_interval': envs.CLEANER_INTERVAL,
                    'tx_updater_api_url': envs.TX_UPDATER_API_URL,
                    'run_tx_cleaner': True,
                    'long_running': True,
                    'epicbox': True,
                    'open': True,
                    })
            }

        await wallet.Call(WalletRequest(**open_wallet))


if __name__ == '__main__':
    if 'PRODUCTION' in os.environ:
        kwargs = dict(host=envs.UVICORN_HOST, port=envs.UVICORN_PORT, lifespan="off", workers=2)
        subprocess.Popen(['python', envs.GRPC_SERVER_PATH])
        time.sleep(2)
        asyncio.run(run_wallet())
    else:
        kwargs = dict(host=envs.UVICORN_HOST, port=envs.UVICORN_PORT, lifespan="off", reload=True)

    uvicorn.run("core.asgi:application", **kwargs)

    try:
        # close running processes
        owner_p = utils.find_process_by_port(envs.WALLET['OWNER_API_PORT'])
        if owner_p:
            utils.logger.info(f"[MAIN    ]: KILLING {psutil.Process(owner_p)}")
            psutil.Process(owner_p).kill()

        grpc_p = utils.find_process_by_port(envs.GRPC_PORT)
        if grpc_p:
            utils.logger.info(f"[MAIN    ]: KILLING {psutil.Process(grpc_p)}")
            psutil.Process(grpc_p).kill()

        epicbox_p = utils.find_process_by_name('epicbox')
        if len(epicbox_p) > 1:
            utils.logger.info(f"[MAIN    ]: KILLING {psutil.Process(epicbox_p[1])}")
            psutil.Process(epicbox_p[1]).kill()

    except Exception:
        pass