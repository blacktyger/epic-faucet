import psutil
import uvicorn

from core.envs import WALLET
from wallet.python_sdk import utils


if __name__ == '__main__':
    uvicorn.run("core.asgi:application", host="127.0.0.1", port=9999, lifespan="off", workers=1)

    # close running owner api
    p = utils.find_process_by_port(WALLET['OWNER_API_PORT'])
    if p:
        print(f">> KILLING {psutil.Process(p)}")
        psutil.Process(p).kill()