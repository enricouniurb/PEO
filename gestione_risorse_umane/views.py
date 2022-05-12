import logging
import io
import csv

from django.conf import settings
from django.contrib.auth.decorators import (login_required,
                                            user_passes_test)
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from datetime import datetime
from django.contrib import messages

from gestione_peo.models import *
from gestione_peo.utils import get_commissioni_attive, get_commissioni_in_corso
from gestione_risorse_umane.models import Dipendente, Avviso
from unical_template.decorators import site_not_in_manteinance
from unical_template.breadcrumbs import BreadCrumbs
from django.core.exceptions import ValidationError

from .forms import *
#from .decorators import matricola_in_csa


logger = logging.getLogger(__name__)


@site_not_in_manteinance
@login_required
#@matricola_in_csa
def dashboard(request):
    """ landing page """

    commissioni_attive = get_commissioni_attive(request.user)
    commissioni_in_corso = get_commissioni_in_corso(request.user,commissioni_attive)

    dipendente = Dipendente.objects.filter(matricola=request.user.matricola).first()
    # creazione dipendente in gestione_risorse_umane se questo non esiste
    if not dipendente:
        dipendente = Dipendente.objects.create(matricola=request.user.matricola,
                                               nome = request.user.first_name,
                                               cognome = request.user.last_name,
                                               utente=request.user)
        dipendente.sync_csa()
    if not dipendente.utente:
        dipendente.utente = request.user
        dipendente.save()

    if dipendente.utente.is_staff:
        bandi = dipendente.idoneita_peo_staff()
    elif dipendente.idoneita_peo_attivata():
        bandi = dipendente.idoneita_peo_attivata()
    else:
        bandi = Bando.objects.none()

    # Escludi i bandi scaduti!
    excluded_pk=[]
    for bando in bandi:
       if not bando.is_in_corso():
           excluded_pk.append(bando.pk)
    bandi = bandi.exclude(pk__in=excluded_pk)

    domande_bando = dipendente.get_domande_progressione()
    for dom in domande_bando:
        for ban in bandi:
            if dom.bando == ban:
                ban.iniziato_dipendente = True

    # dipendente.sync_csa()
    # n = reverse('domande_peo:accetta_condizioni_bando',
                # args=[bandi.first().pk])
    # _logger.error(n)

    d = {
        'commissioni': commissioni_attive,
        'commissioni_in_corso': commissioni_in_corso,
        'dipendente': dipendente,
        'domande_bando': domande_bando,
        'bandi': bandi,
        'MEDIA_URL': settings.MEDIA_URL,
        'avvisi': Avviso.objects.filter(is_active=1),
        }
    return render(request, "dashboard.html", context=d)


@login_required
def upload_carta_identita(request):
    """
        Primo upload o aggiornamento carta identità dipendente
    """
    dipendente = Dipendente.objects.filter(matricola=request.user.matricola).first()

    if request.method == 'POST':
        form = CartaIdentitaForm(request.POST, request.FILES)
        if form.is_valid():
            dipendente.carta_identita_front = request.FILES['carta_identita_front']
            dipendente.carta_identita_retro = request.FILES['carta_identita_retro']
            dipendente.save()
            return HttpResponseRedirect('/')
    else:
        form = CartaIdentitaForm()

    page_title = 'Gestione documento di identità'
    d = {
        'page_title': page_title,
        'breadcrumbs': BreadCrumbs(url_list=(('#', page_title),)),
        'form':form,
        'dipendente': dipendente,
        'MEDIA_URL': settings.MEDIA_URL,
        'IMAGE_TYPES': ', '.join([i.split('/')[1] for i in settings.IMG_PERMITTED_UPLOAD_FILETYPE]),
        'IMAGE_MAX_SIZE': '{} MB.'.format(int(settings.IMG_MAX_UPLOAD_SIZE / (1024.)**2)),
        }
    return render(request, 'upload_carta_identita.html', d)


@user_passes_test(lambda u:u.is_staff)
def import_file(request, nome_modello):
    file_to_import = request.FILES.get('file_to_import')
    if not file_to_import:        
       pass
    url = request.POST.get('next', '/')
    if nome_modello == 'gestione_risorse_umane.FormazioneDipendenteAdmin':    
        # content here
        url = reverse('admin:gestione_risorse_umane_formazionedipendente_changelist')
        if not file_to_import:
            return HttpResponseRedirect(url)
        
        csv_file = request.FILES['file_to_import']
        # let's check if it is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Non è un file di tipo CSV')
            return HttpResponseRedirect(url)

        data_set = ''
        try:
            data_set = csv_file.read().decode(settings.DEFAULT_CHARSET)    
        except:
            csv_file.seek(0)
            data_set = csv_file.read().decode('cp1252')     
        
        # setup a stream which is when we loop through each line we are able to handle a data in a stream
        io_string = io.StringIO(data_set)
        next(io_string)
        for column in csv.reader(io_string, delimiter=';', quotechar="|"):
            if (column[0]):
                _, created = FormazioneDipendente.objects.update_or_create(
                    matricola=_get_matricola(column[0]),
                    partecipante=column[1],
                    evento_formativo=column[2],
                    ente_organizzatore=column[3],
                    data_inizio= datetime.strptime(column[4], '%d/%m/%Y')if column[4] else None,
                    data_fine= datetime.strptime(column[5], '%d/%m/%Y')if column[4] else None,
                    durata_ore = round(float(column[6].replace(',','.')),2) if column[6] else None                    
                )
        context = {}      
 
    if nome_modello == 'gestione_risorse_umane.PrestazioneIndividualeAdmin':    
        # content here
        url = reverse('admin:gestione_risorse_umane_prestazioneindividuale_changelist')
        if not file_to_import:
            return HttpResponseRedirect(url)
        
        csv_file = request.FILES['file_to_import']
        # let's check if it is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Non è un file di tipo CSV')
            return HttpResponseRedirect(url)

        data_set = ''
        try:
            data_set = csv_file.read().decode(settings.DEFAULT_CHARSET)    
        except:
            csv_file.seek(0)
            data_set = csv_file.read().decode('cp1252')     
        
        # setup a stream which is when we loop through each line we are able to handle a data in a stream
        io_string = io.StringIO(data_set)
        next(io_string)
        for column in csv.reader(io_string, delimiter=';', quotechar="|"):
            if (column[0]):
                _, created = PrestazioneIndividuale.objects.update_or_create(
                    matricola=_get_matricola(column[0]),
                    partecipante=column[1],
                    punteggio_finale=column[2],                    
                )
        context = {}        
 
    return HttpResponseRedirect(url)

def _get_matricola(matricola):
    return matricola.zfill(6)