from django.views import generic

from wallet.models import FaucetWallet
from core.envs import WALLET


class HomeView(generic.TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        try:
            context['wallet'] = FaucetWallet.objects.get(name=WALLET['NAME'])
        except:
            pass
        return context