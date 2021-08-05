import logging
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType

from gestione_peo.models import Bando
from .models import *


logger = logging.getLogger(__name__)

def long_running_task(modeladmin, queryset):  
    logger.info('Inizio long_running_task sincronizzazione dipendenti da CSA')
    num_sync = 0
    for i in queryset:
        try:
            if i.sync_csa():
                num_sync += 1
                logger.info('{} Dipendente sincronizzato da CSA'.format(i.matricola))
            else:
                logger.error('Sono incorsi errori nel sincronizzare {}'.format(i.__str__()))
        except Exception as e:        
            logger.exception(e)    
            logger.error('Sono incorsi errori nel sincronizzare {}'.format(i.__str__()))
          
    if num_sync:
       logger.info('{} Dipendenti sincronizzati da CSA'.format(num_sync))