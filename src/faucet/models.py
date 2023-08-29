from _decimal import Decimal
import datetime

from django.utils import timezone
from ipware import get_client_ip
from datetime import timedelta
from django.db import models
import humanfriendly

from core import envs
from wallet.python_sdk.src.utils import parse_uuid, logger
from wallet.python_sdk.src import utils
from core.envs import *

SUCCESS = False
ERROR = True

DECIMALS = Decimal(10 ** 8)


class TxStatus:
    FAILED = 'failed'
    PENDING = 'pending'
    RECEIVED = 'received'
    FINALIZED = 'finalized'


class TxType:
    SENT = 'sent'
    RECEIVED = 'received'


def get_short(address, extra_short: bool = False):
    address = str(address)
    try:
        return f"{address[0:4]}..{address.split('@')[0][-4:]}" if not extra_short else f"{address[0:4]}.."
    except Exception:
        return address

class EpicBoxLogger(models.Model):
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, null=True, related_name='logs')
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.TextField()

    def __str__(self):
        return f"[{self.timestamp.strftime('%m-%d %H:%M')}] {get_short(self.transaction.address)}"


class Address(models.Model):
    """Base class for authorization incoming transaction requests."""
    address = models.CharField(max_length=256)
    is_banned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    manual_lock = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now_add=True)
    last_success_tx = models.DateTimeField(null=True, blank=True)

    def locked_for(self):
        if not self.last_success_tx or not self.is_locked:
            return 0
        else:
            return self.last_success_tx + timedelta(minutes=TIME_LOCK_MINUTES) - timezone.now()

    def locked_msg(self):
        return f'You have reached your limit, try again in ' \
               f'<b>{humanfriendly.format_timespan(self.locked_for().seconds)}</b>.'

    @staticmethod
    def manual_lock_msg():
        return f'You are locked by admin due to abnormal activity (too many requests).'

    @staticmethod
    def too_many_requests_lock_msg():
        return f'You are locked due to abnormal activity in the last 24h (too many requests).'

    async def requests_last_24h(self):
        delta = timezone.now() - datetime.timedelta(days=1)
        return await Transaction.objects.filter(address=self.address, timestamp__gte=delta).acount()

    async def is_now_locked(self):
        if not self.last_success_tx:
            self.is_locked = False
        else:
            self.is_locked = (timezone.now() - self.last_success_tx) < timedelta(minutes=TIME_LOCK_MINUTES)

        await self.asave()
        return self.is_locked

    def __str__(self):
        last_active = self.last_activity.strftime("%m-%d %H:%M") if self.last_activity else ''
        return f"[{last_active}] ReceiverAddress(is_locked='{self.is_locked}', address='{self.address}')"


class ReceiverAddr(Address):
    def __str__(self):
        last_active = self.last_activity.strftime("%m-%d %H:%M") if self.last_activity else ''
        return f"[{last_active}] ReceiverAddress(is_locked='{self.is_locked}', address='{self.address}')"


class IPAddr(Address):
    def __str__(self):
        last_active = self.last_activity.strftime("%m-%d %H:%M") if self.last_activity else ''
        return f"[{last_active}] IPAddr(is_locked='{self.is_locked}', address='{self.address}')"


class Transaction(models.Model):
    address = models.CharField(max_length=256)
    tx_slate_id = models.UUIDField(blank=True, null=True)
    wallet_id = models.CharField(max_length=256, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    archived = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=24, decimal_places=8)
    status = models.CharField(max_length=256)
    height = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=10, default=TxType.SENT)
    fee = models.DecimalField(max_digits=24, decimal_places=8)

    async def update_params(self, **kwargs):
        """Update Transaction parameters in the database"""
        for k, v in kwargs.items():
            setattr(self, k, v)
        await self.asave()

    @staticmethod
    def readable_ints(value: int | str) -> Decimal:
        """Parse big int numbers and return human-readable float/int values"""
        value = Decimal(value)
        return value / DECIMALS

    @classmethod
    async def daily_limit(cls):
        delta = timezone.now() - datetime.timedelta(days=1)
        last_24h_txs = await cls.objects.filter(timestamp__gte=delta, type=TxType.SENT).acount()

        if last_24h_txs > DAILY_LIMIT:
            return utils.response(ERROR, "Faucet's limit for the day is reached, try again tomorrow!")

        return utils.response(SUCCESS, f'Limit not reached yet ({last_24h_txs}/{DAILY_LIMIT})')

    @classmethod
    async def receive_transaction(cls, data: str):
        args = []

        for ele in data.split('['):
            if 'Slate' not in ele:
                args.append(ele.split(']')[0])

        tx = await cls.objects.acreate(
            tx_slate_id=args[0],
            address=args[1],
            amount=Decimal(args[2]),
            status=TxStatus.RECEIVED,
            type=TxType.RECEIVED,
            fee=Decimal('0')
            )

        logger.debug(tx)
        await EpicBoxLogger.objects.acreate(transaction=tx, data=data)

    @classmethod
    async def create_faucet_transaction(cls, address: str, slate: dict, wallet):
        return await cls.objects.acreate(
            tx_slate_id=slate['id'],
            height=slate['height'],
            address=address,
            wallet_id=wallet.id,
            amount=cls.readable_ints(slate['amount']),
            status=TxStatus.PENDING,
            fee=cls.readable_ints(slate['fee'])
            )

    @classmethod
    async def updater_callback(cls, line: str):
        tx_slate_id = parse_uuid(line)

        if tx_slate_id and 'wallet_' not in line:
            tx = await cls.objects.filter(tx_slate_id=tx_slate_id[0]).afirst()

            if tx:
                if 'clear pending' in line:
                    logger.info(f"clean pending transaction [{get_short(tx_slate_id[0])}]")
                    await tx.update_params(status=TxStatus.FAILED)
                    await EpicBoxLogger.objects.acreate(transaction=tx, data=line)

                if "finalized successfully" in line:
                    logger.debug(f"{get_short(tx_slate_id[0])} database updated (finalized)")
                    await tx.update_params(status=TxStatus.FINALIZED)
                    await EpicBoxLogger.objects.acreate(transaction=tx, data=line)

                elif 'error' in line:
                    logger.debug(f"{get_short(tx_slate_id[0])} database updated (failed)")
                    await tx.update_params(status=TxStatus.FAILED)
                    await EpicBoxLogger.objects.acreate(transaction=tx, data=line)

            elif "received from" in line:
                logger.debug(f"Incoming transaction: {get_short(tx_slate_id[0])}")
                await cls.receive_transaction(line)

    @staticmethod
    def validate_tx_args(amount: float | int | str, address: str):
        _address = address.split('@')[0].strip()

        if 'http' in _address:
            _address = _address.split('//')[-1]

        try:
            if 0.00000001 < float(amount) > MAX_AMOUNT:
                return utils.response(ERROR, f'Invalid amount (0 > {amount} < {MAX_AMOUNT})')
            elif len(_address) != 52 or '@epicbox' not in address:
                return utils.response(ERROR, 'Invalid receiver_address')

        except Exception as e:
            return utils.response(ERROR, f'Invalid tx_args, {e}')

        return utils.response(SUCCESS, 'tx_args valid')

    def __str__(self):

        if self.type == TxType.SENT:
            type_ = "->"

            if self.status == TxStatus.FINALIZED:
                icon = "🟢"
            elif self.status == TxStatus.PENDING:
                icon = "🟡"
            elif self.status == TxStatus.FAILED:
                icon = "🔴"
            else:
                icon = "🔘"

        else:
            type_ = "<-"
            icon = "📩"

        return f"[{self.timestamp.strftime('%m-%d %H:%M')}] {icon} {self.amount} {type_} {get_short(self.address)}"


async def connection_details(request, addr, update: bool = False):
    address, created = await ReceiverAddr.objects.aget_or_create(address=addr)
    address.last_activity = timezone.now()

    ip, is_routable = get_client_ip(request, request_header_order=['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'])
    if ip:
        ip, created = await IPAddr.objects.aget_or_create(address=ip)
        ip.last_activity = timezone.now()

    if update:
        await update_connection_details(ip, address)

    return ip, address


async def update_connection_details(ip, address):
    ip_, created = await IPAddr.objects.aget_or_create(address=ip)
    address_, created = await ReceiverAddr.objects.aget_or_create(address=address)

    ip_.last_success_tx = timezone.now()
    await ip_.asave()
    await ip_.is_now_locked()

    address_.last_success_tx = timezone.now()
    await address_.asave()
    await address_.is_now_locked()

    return ip, address


async def connection_authorized(ip, address):
    if await ip.is_now_locked():
        return utils.response(ERROR, ip.locked_msg())

    if ip.manual_lock:
        return utils.response(ERROR, ip.manual_lock_msg())

    if await ip.requests_last_24h() > envs.REQUESTS_PER_DAY:
        return utils.response(ERROR, ip.too_many_requests_lock_msg())

    if await address.is_now_locked():
        return utils.response(ERROR, address.locked_msg())

    if address.manual_lock:
        return utils.response(ERROR, address.manual_lock_msg())

    if await address.requests_last_24h() > envs.REQUESTS_PER_DAY:
        return utils.response(ERROR, address.too_many_requests_lock_msg())

    return utils.response(SUCCESS, 'authorized')
