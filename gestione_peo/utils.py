from . models import CommissioneGiudicatrice, CommissioneGiudicatriceUsers
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType

def get_commissioni_attive(user):
    if not user: return []
    commissioni_utente = CommissioneGiudicatriceUsers.objects.filter(user=user,
                                                                     user__is_active=True)
    commissioni_attive = []
    for cu in commissioni_utente:
        if cu.commissione.is_active:
            commissioni_attive.append(cu.commissione)
    return commissioni_attive

def get_commissioni_in_corso(user, commissioni_attive=[]):
    if not user: return []
    if not commissioni_attive:
        commissioni_attive = get_commissioni_attive(user)
    commissioni_in_corso = []
    for c in commissioni_attive:
        if c.is_in_corso():
            commissioni_in_corso.append(c)
    return commissioni_in_corso

def calcolo_punteggio_domanda_log_save(domanda_bando, messages, request):
    results = domanda_bando.calcolo_punteggio_domanda(save=True)           
    punteggio = results[1]
    msg = ("Punteggio calcolato con successo "
        "({}) per la domanda {}").format(punteggio,
                                            domanda_bando)
    # mostra il messaggio
    messages.add_message(request, messages.SUCCESS, msg)
    
    for m in results[2]:
        messages.add_message(request, messages.WARNING, m)

    # Logging di ogni azione compiuta sulla domanda dalla commissione
    LogEntry.objects.log_action(user_id = request.user.pk,
                                content_type_id = ContentType.objects.get_for_model(domanda_bando).pk,
                                object_id       = domanda_bando.pk,
                                object_repr     = domanda_bando.__str__(),
                                action_flag     = CHANGE,
                                change_message  = msg)