import logging
import io
import json

from django.apps import apps
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.http.response import HttpResponse

from gestione_peo.models import Bando
from .models import *

import threading 

from django_auto_serializer.auto_serializer import (SerializableInstance,
                                                    ImportableSerializedInstance)

from .tasks import long_running_task

logger = logging.getLogger(__name__)

def abilita_idoneita_peo(modeladmin, request, queryset):
    bando = Bando.objects.filter(redazione=True).last()
    msg_bando_not_valid = ('Nessun Bando attivo. '
                           'Prova a configurare "redazione" '
                           'al Bando di riferimento e a controllare '
                           'che questo non sia scaduto.')
    if not bando:
        messages.add_message(request, messages.ERROR, msg_bando_not_valid)
        return
    elif bando.is_scaduto():
        messages.add_message(request, messages.ERROR, msg_bando_not_valid)
        return
    
    abilitati_peo_model = apps.get_model(app_label='domande_peo',
                                         model_name='AbilitazioneBandoDipendente')
    #dip_pk = []
    for dip in queryset:
        if dip.disattivato:
            messages.add_message(request, messages.ERROR,
                                "Il dipendente {} si trova in stato "
                                "'disattivato'. Per procedere all'abilitazione "
                                " occorre modificare questo parametro".format(dip))
            continue
        #if dip.idoneita_peo():
        messages.add_message(request, messages.INFO,
        '{} idoneo a {}. Dipendente correttamente inserito tra gli abilitati.'.format(dip, bando, ''))
        abilitato = abilitati_peo_model.objects.create(bando=bando, dipendente=dip)
        #dip_pk.append(abilitato.pk)
        # else:
            # messages.add_message(request, messages.WARNING,
                                 # '{} non idoneo a {}'.format(dip, bando))

    # abilitati_preesistenti = abilitati_peo_model.objects.exclude(bando=bando,
                                                                 # dipendente__pk__in=dip_pk)
    # for ap in abilitati_preesistenti:
        # msg = '{} risulta essere abilitato ma non nel calcolo attuale. Verifica se legittimo.'
        # messages.add_message(request, messages.WARNING,
        # msg.format(ap.dipendente))
    
abilita_idoneita_peo.short_description = "Abilita i selezionati a partecipare al Bando in Redazione"

def disabilita_idoneita_peo(modeladmin, request, queryset):
    bando = Bando.objects.filter(redazione=True).last()
    msg_bando_not_valid = ('Nessun Bando attivo. '
                           'Prova a configurare "redazione" '
                           'al Bando di riferimento e a controllare '
                           'che questo non sia scaduto.')
    if not bando:
        messages.add_message(request, messages.ERROR, msg_bando_not_valid)
        return
    elif bando.is_scaduto():
        messages.add_message(request, messages.ERROR, msg_bando_not_valid)
        return
    
    abilitati_peo_model = apps.get_model(app_label='domande_peo',
                                         model_name='AbilitazioneBandoDipendente')
    for dip in queryset:
        #if dip.idoneita_peo():
        messages.add_message(request, messages.WARNING,
        '{} idoneo a {}. Dipendente correttamente rimosso dagli abilitati.'.format(dip, bando, ''))
        abilitato = abilitati_peo_model.objects.filter(bando=bando, dipendente=dip)
        abilitato.delete()
    
disabilita_idoneita_peo.short_description = "Disabilita i selezionati a partecipare al Bando in Redazione"


def sincronizza_da_csa(modeladmin, request, queryset):
    num_sync = 0
    for i in queryset:
        try:
            if i.sync_csa():
                num_sync += 1
            else:
                messages.add_message(request, messages.ERROR, 'Sono incorsi errori nel sincronizzare {}'.format(i.__str__()))
        except Exception as e:        
            logger.exception(e)    
            messages.add_message(request, messages.ERROR, 'Sono incorsi errori nel sincronizzare {}'.format(i.__str__()))
    if num_sync:
        messages.add_message(request, messages.INFO, '{} Dipendenti sincronizzati da CSA'.format(num_sync))

sincronizza_da_csa.short_description = "Sincronizza i dati dei dipendenti selezionati da CSA"

def async_sincronizza_da_csa(modeladmin, request, queryset):
    t = threading.Thread(target=long_running_task, args=(modeladmin, queryset, ), kwargs={})
    t.setDaemon(True)
    t.start()
    
    messages.add_message(request, messages.INFO, 'Sincronizzazione in fase di esecuzione')

async_sincronizza_da_csa.short_description = "Sincronizza asincrona i dati dei dipendenti selezionati da CSA"    


def scarica_template(modeladmin, request, queryset):
    iofile = io.StringIO()    
    for entity in queryset:
        try:
            si = SerializableInstance(entity)
            st = si.serialize_tree()
            iofile.write(json.dumps(si.dict, indent=2))
        except Exception as e:
            msg = '{} duplicazione fallita: {}'
            messages.add_message(request, messages.WARNING,
                                 msg.format(entity, e))        
    file_name = 'peo_template_{}.json'.format(type(modeladmin).__name__)
    iofile.seek(0)
    response = HttpResponse(iofile.read())
    response['content_type'] = 'application/force-download'
    response['Content-Disposition'] = 'attachment; filename={}'.format(file_name)
    response['X-Sendfile'] = file_name
    return response
scarica_template.short_description = "Scarica Template"