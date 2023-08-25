from django.contrib import admin
from .models import *


class TransactionInline(admin.TabularInline):
    model = EpicBoxLogger
    max_num = 1


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [TransactionInline, ]


admin.site.register((EpicBoxLogger, ReceiverAddr, IPAddr))