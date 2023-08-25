# Create your views here.
from django.views import generic


class HomeView(generic.TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['wallet_balance'] = 0.0
        return context