import asyncio
import json
import uuid
import os

from django.db import models

from django.contrib import admin
from .python_sdk import Wallet as EpicWallet
from core.envs import WALLET


class FaucetWallet (models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=32, default=WALLET['NAME'])
    balance = models.JSONField(default=dict, blank=True)
    password = models.CharField(max_length=32, default=WALLET['PASSWORD'])
    binary_path = models.CharField(max_length=256, default=WALLET['BINARY_PATH'])
    node_address = models.CharField(max_length=128, default=WALLET['NODE_ADDRESS'])
    owner_api_port = models.IntegerField(default=WALLET['OWNER_API_PORT'])
    wallet_directory = models.CharField(max_length=256, default=WALLET['WALLET_DIR'])

    wallet: EpicWallet = None

    def updater(self, interval: int):
        async def updater_():
            while True:
                balance = await self.wallet.get_balance()
                self.balance = json.loads(balance.json())
                await self.asave()
                await asyncio.sleep(interval)

        asyncio.run(updater_())

    def get_wallet(self):
        if not os.path.isdir(WALLET['WALLET_DIR']):
            print(f'>> CREATING NEW EPIC-WALLET')
            asyncio.run(self.create_new())

        self.wallet = EpicWallet(path=self.wallet_directory, long_running=True)
        return self.wallet

    @classmethod
    async def create_new(cls, **kwargs):
        if not kwargs:
            kwargs = {
                'name': WALLET['NAME'],
                'debug': True,
                'password': WALLET['PASSWORD'],
                'node_address': WALLET['NODE_ADDRESS'],
                'binary_file_path': WALLET['BINARY_PATH'],
                'wallet_data_directory': WALLET['WALLET_DIR'],
                'owner_api_listen_port': WALLET['OWNER_API_PORT'],
                }

        return await EpicWallet().create_new(**kwargs)

    def __str__(self):
        return f"{self.balance['amount_currently_spendable'] if self.balance else '0.00'}"


admin.site.register(FaucetWallet)