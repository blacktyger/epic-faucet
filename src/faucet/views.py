import asyncio
import signal
import json
import sys

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from django.views import generic

from faucet.models import Transaction, TxType, TxStatus, ReceiverAddr
from django.http.response import StreamingHttpResponse
from wallet.models import FaucetWallet
from core.envs import WALLET


def signal_handler(signal, frame):
    sys.exit(0)

class HomeView(generic.TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        try:
            context['wallet'] = FaucetWallet.objects.get(name=WALLET['NAME'])
        except:
            pass
        return context


async def iterator():
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        txs = Transaction.objects.all()
        total = await txs.filter(type=TxType.SENT).acount()
        sent = await txs.filter(type=TxType.SENT).aaggregate(Sum('amount'))
        sent = float(sent['amount__sum'])
        received = await txs.filter(type=TxType.RECEIVED).aaggregate(Sum('amount'))
        received = float(received['amount__sum'])
        finalized = await txs.filter(status=TxStatus.FINALIZED).acount()
        failed = await txs.filter(status=TxStatus.FAILED).acount()
        pending = await txs.filter(status=TxStatus.PENDING).acount()
        update = timezone.now().strftime("%H:%M UTC")

        unique_users = await ReceiverAddr.objects.all().acount()

        data = json.dumps({
            'txTotal': total,
            'txClaimed': sent,
            'txDeposited': received,
            'txFinalized': finalized,
            'txFailed': failed,
            'txPending': pending,
            'users': unique_users,
            'update': update,
            })

        yield f'data:{data}\n\n'
        await asyncio.sleep(60)


def stats_stream(request):
    stream = iterator()
    response = StreamingHttpResponse(stream, status=200, content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response.headers["X-Accel-Buffering"] = "no"
    return response


def stats(request):
    context = {'fields': ['Total', 'Finalized', 'Pending', 'Failed', 'Deposited', 'Claimed']}
    return render(request, 'stats.html', context)
