import logging
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType

from gestione_peo.models import Bando
from .models import *


logger = logging.getLogger(__name__)

def long_running_task(modeladmin, queryset):  
    num_sync = 0
    for i in queryset:
        if i.sync_csa():
            num_sync += 1
        else:
           logger.error( 'Sono incorsi errori nel sincronizzare {}'.format(i.__str__()))
    if num_sync:
       logger.info('{} Dipendenti sincronizzati da CSA'.format(num_sync))