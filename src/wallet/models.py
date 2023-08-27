import asyncio
import json
import uuid
import os

from django.contrib import admin
from django.db import models

from .python_sdk.src import Wallet as EpicWallet
from core.envs import WALLET


class FaucetWallet (models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=32, default=WALLET['NAME'])
    balance = models.JSONField(default=dict, blank=True)
    node_address = models.CharField(max_length=128, default=WALLET['NODE_ADDRESS'])
    epicbox_address = models.CharField(max_length=124, blank=True)
    created_at_height = models.IntegerField(null=True)

    wallet: EpicWallet = None

    def display_balance(self):
        if self.balance:
            return round(self.balance['amount_currently_spendable'] + self.balance['amount_awaiting_finalization'], 3)

    def full_balance(self):
        if self.balance:
            spendable = round(self.balance['amount_currently_spendable'], 3)
            pending = round(self.balance['amount_awaiting_finalization'] + self.balance['amount_awaiting_confirmation'], 3)
            return f"Spendable: {spendable if spendable else '0.00'} \n" \
                   f"Pending: {pending if pending else '0.00'}"

    async def create_new(self, **kwargs):
        if not kwargs:
            kwargs = {
                'id': str(self.id),
                'name': self.name,
                'debug': True,
                'password': WALLET['PASSWORD'],
                'node_address': self.node_address,
                'binary_file_path': WALLET['BINARY_PATH'],
                'wallet_data_directory': WALLET['WALLET_DIR'],
                'owner_api_listen_port': WALLET['OWNER_API_PORT'],
                }

        wallet = await EpicWallet().create_new(**kwargs)
        self.epicbox_address = wallet.config.epicbox_address
        self.created_at_height = wallet.config.created_at_height
        self.save()

    def __str__(self):
        return f"Wallet({self.name} {self.balance['amount_currently_spendable'] if self.balance else '0.00'})"


admin.site.register(FaucetWallet)