import csv
import json
import magic
import os
import shutil

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.http.response import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.forms.models import model_to_dict

from django_form_builder.utils import (get_allegati,
                                       get_allegati_dict,
                                       get_as_dict,
                                       get_labeled_errors,
                                       get_POST_as_json,
                                       set_as_dict)

from domande_peo.models import *
from gestione_peo.models import Bando, IndicatorePonderato, DescrizioneIndicatore
from gestione_peo.settings import ETICHETTA_INSERIMENTI_ID
from gestione_risorse_umane.models import Dipendente, PosizioneEconomica, LivelloPosizioneEconomica


def get_fname_allegato(domanda_bando_id, bando_id):
    return "domanda_{}-{}.pdf".format(domanda_bando_id, bando_id)


def get_path_allegato(matricola, slug_bando, id_modulo_inserito):
    """
        Costruisce il path dei file relativi agli allegati e lo restituisce
    """
    path = '{}/{}/{}/bando-{}/domanda-id-{}'.format(settings.MEDIA_ROOT,
                                                    settings.DOMANDE_PEO_FOLDER,
                                                    matricola,
                                                    slug_bando,
                                                    id_modulo_inserito)
    return path


def salva_file(f, path, nome_file):
    file_path = '{}/{}'.format(path,nome_file)

    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with open(file_path,'wb') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def download_file(path, nome_file):
    """
        Effettua il download di un file
    """
    mime = magic.Magic(mime=True)
    file_path = '{}/{}'.format(path,nome_file)
    content_type = mime.from_file(file_path)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=content_type)
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    return None


def elimina_file(path, nome_file):
    """
        Elimina un file allegato a una domanda dal disco
    """

    file_path = '{}/{}'.format(path,nome_file)
    try:
        os.remove(file_path)
        return path
    except:
        return False


def elimina_directory(matricola, bando_slug, modulo_compilato_id = None):
    """
        Rimuove dal disco ricorsivamente una cartella.
        Se il parametro 'modulo_compilato_id' NON viene fornito, la funzione
        cancella la directory 'matricola' che raccoglie gli allegati della Domanda PEO.
        Se, invece, il parametro viene fornito, allora verrà cancellata solo
        la directory con gli allegati del ModuloCompilato.
    """
    path = '{}/{}/{}/bando-{}'.format(settings.MEDIA_ROOT,
                                               settings.DOMANDE_PEO_FOLDER,
                                               matricola,
                                               bando_slug)
    if modulo_compilato_id:
        path = path + '/domanda-id-{}'.format(modulo_compilato_id)

    try:
        shutil.rmtree(path)
        return path
    except:
        return False


def export_graduatoria_indicatori_ponderati_csv(queryset, fopen,
                           delimiter=';', quotechar='"',
                           replace_dot_with='.',
                           ignora_disabilitati=False):
    # domande_bando selezionate
    queryset = queryset.order_by('-punteggio_calcolato')
    posizioni_economiche = PosizioneEconomica.objects.all().order_by('nome')

    bando = queryset.first().bando
    #Recupero tutti gli indcatori del bando in questione
    indicatori_ponderati = bando.indicatoreponderato_set.all().order_by('ordinamento')
   
    intestazione = ['Prog', 'Matricola', 'Cognome', 'Nome', 'Data ultimo avanzamento ' ,'Pos.Eco']

    writer = csv.writer(fopen,
                        delimiter = delimiter,
                        quotechar = quotechar)
    intestazione2 = []
    lista_id_indicatore = []
    # Creo le colonne dell'intestazione (Nome + ID code)
    # Per ogni IndicatorePonderato del Bando
    for indicatore in indicatori_ponderati:    
        intestazione2.append('({}) {}'.format(indicatore.id_code, indicatore.nome))
        lista_id_indicatore.append(indicatore.id_code)
        
    intestazione += intestazione2    
    intestazione.append('Punti')
    writer.writerow(intestazione)

    # Per ogni posizione economica, controllo se ci sono domande
    # cosi da ordinarle e avere una graduatoria
    for pos_eco in posizioni_economiche:
        livelli = LivelloPosizioneEconomica.objects.filter(posizione_economica=pos_eco).all().order_by('nome')
        for livello in livelli:
            # Filtro solo le domande con il livello economico che mi interessa
            domande_queryset = queryset.filter(livello=livello)
            # Se non ci sono domande nel livello, non scrivo righe
            if not domande_queryset: continue
            writer.writerow('')
            index = 1
            # Per ogni domanda del bando, recupero quelle fatte per
            # un singolo Livello Economico
            for domanda in domande_queryset:
                # Se la domanda non è stata chiusa almeno una volta
                if not domanda.numero_protocollo: continue
                riga = [index,
                        domanda.dipendente.matricola.zfill(6),
                        domanda.dipendente.cognome,
                        domanda.dipendente.nome,
                        domanda.data_ultima_progressione,
                        livello.__str__()]
                
              
                # Per ogni Indicatore ponderato nell'intestazione
                for id_code in lista_id_indicatore:
                    # Soglia massima assegnabile
                    p_max_indicatore = indicatore.get_pmax_pos_eco(pos_eco)
                    # Punteggio assegnato all'Indicatore Ponderato
                    p_indicatore = 0
                    # Punteggio assegnato all'Indicatore Ponderato senza soglie
                    p_indicatore_senza_soglie = 0
                    # Recupero l'oggetto                    
                    indicatore = indicatori_ponderati.filter(id_code=id_code).first()    
                    if id_code == 'D':
                        # Anzianità Dipendente Università
                        p_indicatore = domanda.get_punteggio_anzianita()    
                    elif id_code == 'C':
                        # Prestazione individuale
                        p_indicatore = domanda.get_prestazione_individuale()                
                    else:    
                                       
                        for descr_ind in indicatore.descrizioneindicatore_set.filter(calcolo_punteggio_automatico=True):   
                            # Recupero il punteggio max assegnato nella domanda         
                            #  Lista ritornata come risultato
                            # [0] = punteggio ottenuto senza tener conto di alcuna soglia
                            # [1] = punteggio reale assegnato (max)
                            # [2] = eventuale messaggio di sforamento           
                            punteggio = domanda.calcolo_punteggio_max_descr_ind(descr_ind=descr_ind,
                                                                                categoria_economica=pos_eco,
                                                                                ignora_disabilitati=ignora_disabilitati)
                            p_indicatore_senza_soglie += punteggio[0]
                            p_indicatore += punteggio[1]
                    # Controllo sul Max punteggio CatEco IndicatorePonderato
                    if p_max_indicatore > 0 and p_indicatore > p_max_indicatore:
                        p_indicatore =  p_max_indicatore
                    riga.append(p_indicatore.__str__().replace('.', replace_dot_with))

                punteggio_domanda = domanda.calcolo_punteggio_domanda(ignora_disabilitati=ignora_disabilitati)[1]
                punteggio_str = punteggio_domanda.__str__().replace('.', replace_dot_with)
                riga.append(punteggio_str)

                writer.writerow(riga)
                index += 1

    writer.writerow('')
    return fopen

def export_graduatoria_csv(queryset, fopen,
                           delimiter=';', quotechar='"',
                           replace_dot_with='.',
                           ignora_disabilitati=False):
    """
    Esporta la graduatoria dei partecipanti,
    fopen può essere un oggetto response oppure un fopen
    """
    # domande_bando selezionate
    queryset = queryset.order_by('-punteggio_calcolato')
    posizioni_economiche = PosizioneEconomica.objects.all().order_by('nome')
    #Recupero tutti i DescrInd del bando in questione
    descr_ind = DescrizioneIndicatore.objects.filter(indicatore_ponderato__bando = queryset.first().bando).all().order_by('id_code')

    intestazione = ['Prog', 'Cognome', 'Nome', 'Pos.Eco']

    writer = csv.writer(fopen,
                        delimiter = delimiter,
                        quotechar = quotechar)
    intestazione2 = []
    lista_id_descr = []
    # Creo le colonne dell'intestazione (Nome + ID code)
    for di in descr_ind:
        if di.calcolo_punteggio_automatico:
            intestazione2.append('({}) {}'.format(di.id_code, di.nome))
            lista_id_descr.append(di.id_code)
    intestazione += intestazione2
    intestazione.append('Qualità delle prestazioni individuali')
    intestazione.append('Anzianità presso Università')
    intestazione.append('Punti')
    writer.writerow(intestazione)

    # Per ogni posizione economica, controllo se ci sono domande
    # cosi da ordinarle e avere una graduatoria
    for pos_eco in posizioni_economiche:
        livelli = LivelloPosizioneEconomica.objects.filter(posizione_economica=pos_eco).all().order_by('nome')
        for livello in livelli:
            # Filtro solo le domande con il livello economico che mi interessa
            domande_queryset = queryset.filter(livello=livello)
            # Se non ci sono domande nel livello, non scrivo righe
            if not domande_queryset: continue
            writer.writerow('')
            index = 1
            # Per ogni domanda del bando, recupero quelle fatte per
            # un singolo Livello Economico
            for domanda in domande_queryset:
                # Se la domanda non è stata chiusa almeno una volta
                if not domanda.numero_protocollo: continue
                riga = [index,
                        domanda.dipendente.cognome,
                        domanda.dipendente.nome,
                        livello.__str__()]
                # Per ogni DescrInd nell'intestazione
                for descr in lista_id_descr:
                    # Recupero l'oggetto
                    d = descr_ind.filter(id_code=descr).first()
                    # Recupero il punteggio max assegnato nella domanda
                    punteggio = domanda.calcolo_punteggio_max_descr_ind(descr_ind=d,
                                                                        categoria_economica=livello,
                                                                        ignora_disabilitati=ignora_disabilitati)[1]
                    riga.append(punteggio.__str__().replace('.', replace_dot_with))
                
                # Qualità delle prestazioni indivuali
                riga.append(domanda.get_prestazione_individuale().__str__().replace('.', replace_dot_with))
                # Anzianità Dipendente Università
                riga.append(domanda.get_punteggio_anzianita().__str__().replace('.', replace_dot_with))

                # Punteggio totale

                # In origine il valore del punteggio totale era quello
                # impostato dal calcolo punteggio effettuato in precedenza.
                # Ma se questo non esiste o se si sceglie di ignorare gli inserimenti
                # disabilitati, il dato non sarebbe affidabile.
                # Allora si recupera dinamicamente il punteggio
                # tramite il metodo domanda.calcolo_punteggio_domanda(ignora_disabilitati=ignora_disabilitati)
                # con parametro save=False di default, in modo che questa operazione
                # non vada a sovrascrivere un eventuale punteggio calcolato in precedenza.
                # Questo comporta naturalmente un aggravio prestazionale.

                # riga.append(domanda.punteggio_calcolato.__str__().replace('.', replace_dot_with))
                punteggio_domanda = domanda.calcolo_punteggio_domanda(ignora_disabilitati=ignora_disabilitati)[1]
                punteggio_str = punteggio_domanda.__str__().replace('.', replace_dot_with)
                riga.append(punteggio_str)

                writer.writerow(riga)
                index += 1
            writer.writerow('')
    return fopen

def aggiungi_titolo_from_db(request,
                         datadb,
                         bando,
                         descrizione_indicatore,
                         domanda_bando,
                         dipendente,                       
                         log=False,
                         checked=False,
                         tipo_caricamento_modulo = 'automatico'):
    
    form = descrizione_indicatore.get_form(data = datadb,                                           
                                           domanda_bando=domanda_bando)
    if form.is_valid() or checked:
        # qui chiedere conferma prima del salvataggio
        #json_data = get_POST_as_json(request)
        mdb_model = apps.get_model(app_label='domande_peo', model_name='ModuloDomandaBando')
        mdb = mdb_model.objects.create(
                domanda_bando = domanda_bando,
                modulo_compilato = json.dumps(datadb, indent = 2),
                descrizione_indicatore = descrizione_indicatore,
                modified=timezone.localtime(),
                tipo_caricamento_modulo=tipo_caricamento_modulo
                )

        msg = 'Inserimento {} - Etichetta: {} - effettuato con successo!'.format(mdb, datadb[ETICHETTA_INSERIMENTI_ID])   
        #Allega il messaggio al redirect
        messages.success(request, msg)
        if log:
            LogEntry.objects.log_action(user_id = request.user.pk,
                                        content_type_id = ContentType.objects.get_for_model(domanda_bando).pk,
                                        object_id       = domanda_bando.pk,
                                        object_repr     = domanda_bando.__str__(),
                                        action_flag     = CHANGE,
                                        change_message  = msg)

def aggiungi_titolo_form(request,
                         bando,
                         descrizione_indicatore,
                         domanda_bando,
                         dipendente,
                         return_url,
                         log=False):
                         
    form = descrizione_indicatore.get_form(data=request.POST,
                                           files=request.FILES,
                                           domanda_bando=domanda_bando)
    if form.is_valid():
        # qui chiedere conferma prima del salvataggio
        json_data = get_POST_as_json(request)
        mdb_model = apps.get_model(app_label='domande_peo', model_name='ModuloDomandaBando')
        mdb = mdb_model.objects.create(
                domanda_bando = domanda_bando,
                modulo_compilato = json_data,
                descrizione_indicatore = descrizione_indicatore,
                modified=timezone.localtime(),
                )

        # salvataggio degli allegati nella cartella relativa
        # Ogni file viene rinominato con l'ID del ModuloDomandaBando
        # appena creato e lo "slug" del campo FileField
        # json_stored = mdb.get_as_dict()
        json_dict = json.loads(mdb.modulo_compilato)
        json_stored = get_as_dict(json_dict)
        if request.FILES:
            json_stored["allegati"] = {}
            path_allegati = get_path_allegato(dipendente.matricola,
                                              bando.slug,
                                              mdb.pk)
            if 'sub_descrizione_indicatore_form' in json_stored:
                current_value = json_stored['sub_descrizione_indicatore_form']
                for key, value in request.FILES.items():                         
                    if (key.endswith('submulti_{}'.format(current_value)) or 'submulti' not in key):               
                        salva_file(request.FILES[key],
                                    path_allegati,
                                    request.FILES[key]._name)
                        json_stored["allegati"]["{}".format(key)] = "{}".format(request.FILES[key]._name)                           
            else:
                for key, value in request.FILES.items():                                        
                    salva_file(request.FILES[key],
                                path_allegati,
                                request.FILES[key]._name)
                    json_stored["allegati"]["{}".format(key)] = "{}".format(request.FILES[key]._name)

        set_as_dict(mdb, json_stored)
        # mdb.set_as_dict(json_stored)
        domanda_bando.mark_as_modified()
        msg = 'Inserimento {} - Etichetta: {} - effettuato con successo!'.format(mdb,
                                                                                 request.POST.get(ETICHETTA_INSERIMENTI_ID))                                                                                       
        #Allega il messaggio al redirect
        messages.success(request, msg)
        if log:
            LogEntry.objects.log_action(user_id = request.user.pk,
                                        content_type_id = ContentType.objects.get_for_model(domanda_bando).pk,
                                        object_id       = domanda_bando.pk,
                                        object_repr     = domanda_bando.__str__(),
                                        action_flag     = CHANGE,
                                        change_message  = msg)
        # url = reverse('gestione_peo:commissione_domanda_manage', args=[commissione.pk, domanda_bando.pk,])
        return HttpResponseRedirect(return_url)
    else:
        dictionary = {}
        # il form non è valido, ripetere inserimento
        dictionary['form'] = form
        return dictionary


def modifica_titolo_form(request,
                         bando,
                         descrizione_indicatore,
                         mdb,
                         allegati,
                         path_allegati,
                         return_url,
                         log=False):
    json_response = json.loads(get_POST_as_json(request))
    # Costruisco il form con il json dei dati inviati e tutti gli allegati
    json_response["allegati"] = allegati
    # rimuovo solo gli allegati che sono stati già inseriti
    form = descrizione_indicatore.get_form(data=json_response,
                                           files=request.FILES,
                                           domanda_bando=mdb.domanda_bando,
                                           remove_filefields=allegati)
    if form.is_valid():
        if request.FILES:
            for key, value in request.FILES.items():
                # form.validate_attachment(request.FILES[key])
                salva_file(request.FILES[key],
                            path_allegati,
                            request.FILES[key]._name)
                nome_allegato = request.FILES[key]._name
                json_response["allegati"]["{}".format(key)] = "{}".format(nome_allegato)
        else:                    
            # Se non ho aggiornato i miei allegati lasciandoli invariati rispetto
            # all'inserimento precedente            
            json_response["allegati"] = allegati

        if 'sub_descrizione_indicatore_form' in json_response:
            current_value = json_response['sub_descrizione_indicatore_form']
            #eliminare tutti gli allegati diversi da current_value
            copy_allegati = allegati.copy()
            for allegato in copy_allegati.keys():            
                if ('submulti_' in allegato and not (allegato.endswith('submulti_{}'.format(current_value)))):
                    nome_file = json_response["allegati"]["{}".format(allegato)]
                    # Rimuove il riferimento all'allegato dalla base dati
                    del json_response["allegati"]["{}".format(allegato)]       
                    # Rimuove l'allegato dal disco
                    elimina_file(path_allegati, nome_file)


        # salva il modulo
        set_as_dict(mdb, json_response)
        if mdb.tipo_caricamento_modulo == 'automatico':
             mdb.tipo_caricamento_modulo = 'automatico_mod'
             mdb.save()
        # data di modifica
        mdb.mark_as_modified()
        #Allega il messaggio al redirect
        msg = 'Modifica {} - Etichetta: {} - effettuata con successo!'.format(mdb,
                                                                              request.POST.get(ETICHETTA_INSERIMENTI_ID))
        messages.success(request, msg)
        if log:
            LogEntry.objects.log_action(user_id = request.user.pk,
                                        content_type_id = ContentType.objects.get_for_model(mdb.domanda_bando).pk,
                                        object_id       = mdb.domanda_bando.pk,
                                        object_repr     = mdb.domanda_bando.__str__(),
                                        action_flag     = CHANGE,
                                        change_message  = msg)
        return HttpResponseRedirect(return_url)
    else:
        dictionary = {}
        # il form non è valido, ripetere inserimento
        dictionary['form'] = form
        return dictionary


def elimina_allegato_from_mdb(request,
                              bando,
                              dipendente,
                              mdb,
                              allegato,
                              return_url,
                              log=False):
    # json_stored = mdb.get_as_dict()
    json_dict = json.loads(mdb.modulo_compilato)
    json_stored = get_as_dict(json_dict)
    nome_file = json_stored["allegati"]["{}".format(allegato)]

    # Rimuove il riferimento all'allegato dalla base dati
    del json_stored["allegati"]["{}".format(allegato)]

    # mdb.set_as_dict(json_stored)
    set_as_dict(mdb, json_stored)
    mdb.mark_as_modified()
    mdb.domanda_bando.mark_as_modified()

    path_allegato = get_path_allegato(dipendente.matricola,
                                      bando.slug,
                                      mdb.pk)
    # Rimuove l'allegato dal disco
    elimina_file(path_allegato, nome_file)
    etichetta = mdb.get_identificativo_veloce()
    msg = 'Allegato {} eliminato con successo da {} - Etichetta: {}'.format(nome_file,
                                                                            mdb,
                                                                            etichetta)
    if log:
        LogEntry.objects.log_action(user_id = request.user.pk,
                                    content_type_id = ContentType.objects.get_for_model(mdb.domanda_bando).pk,
                                    object_id       = mdb.domanda_bando.pk,
                                    object_repr     = mdb.domanda_bando.__str__(),
                                    action_flag     = CHANGE,
                                    change_message  = msg)
    return HttpResponseRedirect(return_url)


def cancella_titolo_from_domanda(request,
                                 bando,
                                 dipendente,
                                 mdb,
                                 return_url,
                                 mark_domanda_as_modified=True,
                                 log=False):
    if mark_domanda_as_modified:
        mdb.domanda_bando.mark_as_modified()
    # Rimuove la folder relativa al modulo compilato,
    # comprensiva di allegati ('modulo_compilato_id' passato come argomento)
    elimina_directory(dipendente.matricola, bando.slug, mdb.pk)
    etichetta = mdb.get_identificativo_veloce()
    msg = 'Modulo {} - Etichetta: {} - rimosso con successo!'.format(mdb, etichetta)
    if log:
        LogEntry.objects.log_action(user_id = request.user.pk,
                                    content_type_id = ContentType.objects.get_for_model(mdb.domanda_bando).pk,
                                    object_id       = mdb.domanda_bando.pk,
                                    object_repr     = mdb.domanda_bando.__str__(),
                                    action_flag     = CHANGE,
                                    change_message  = msg)
    mdb.delete()
    messages.success(request, msg)
    return HttpResponseRedirect(return_url)


def download_allegato_from_mdb(bando,
                               mdb,
                               dipendente,
                               allegato):
    # json_stored = mdb.get_as_dict()
    json_dict = json.loads(mdb.modulo_compilato)
    json_stored = get_as_dict(json_dict)
    nome_file = json_stored["allegati"]["{}".format(allegato)]

    path_allegato = get_path_allegato(dipendente.matricola,
                                      bando.slug,
                                      mdb.pk)
    result = download_file(path_allegato,
                           nome_file)

    if result is None: raise Http404
    return result


def test_allegati(bando,
                  backup_folder='/opt/django_peo_dumps/backup_replica/media/media/domande_peo/',
                  restore=False):
    for i in DomandaBando.objects.filter(bando=bando):
        for m in i.modulodomandabando_set.all():
            p = m.get_allegati_path()
            if len(p) >= 1:
                p = p[0]
                if not os.path.exists(p):
                    print('Errore in {}: {}'.format(i, p))

                    if backup_folder:
                        pp = p.replace(base_path, backup_folder)
                        if not os.path.exists(pp):
                            print('  Non recuperabile: {}'.format(pp))
                            failed.append(pp)
                        else:
                            print('  Recuperabile in: {}'.format(pp))
                            fname = pp.split('/')[-1]
                            bdir = base_path + '/{}/bando-{}'.format(i.dipendente.matricola,
                                                                    bando.slug,)
                            dest_dir =  bdir + '/domanda-id-{}/'.format(m.pk)
                            dest_complete = dest_dir+fname
                            print('  ... Copy "{}"\n      into: "{}"'.format(pp, dest_complete))
                            if restore:
                                if not os.path.exists(bdir):
                                    os.mkdir(bdir)
                                if not os.path.exists(dest_dir):
                                    os.mkdir(dest_dir)
                                shutil.copyfile(pp, dest_complete)
