from datetime import datetime

from django.conf import settings
from django.utils import timezone

def differenza_date_in_mesi_aru(dt, now=None):
    """
    calcola quanti mesi sono trascorsi tra la data dt e new
    secondo il modello ARU, dove per mese si intendono almeno 15 giorni + 1
    all'interno dell'ultimo mese considerabile.
    """
    if now:
        mo = now
    else:
        mo = timezone.localtime()

    anni = mo.year - dt.year
    mesi =  mo.month - dt.month
    giorni = mo.day - dt.day + 1

    if giorni > 15:
        mesi = mesi + 1
    elif giorni <= -15:
        mesi = mesi - 1

    return mesi + 12*anni

def parse_date_string(dt):
    """
    Crea un date() a partire da una stringa.
    Il formato deve rispettare le limitazioni imposte nel SETTINGS
    """
    if not dt:
        return False

    for formato in settings.DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(dt, formato).date()
        except ValueError:
            pass
    raise ValueError('Formato della data non valido')

def text_as_html(text):
    """
    Sostituisce '\n' con '<br>' in un testo
    """
    return text.replace('\n', '<br>')

def punteggio_ogni_3_ore(pt, durata):    
    return (durata // 3) * pt + (pt if (durata % 3) >= 1.5 else 0)

def punteggio_ogni_3_ore_max_02(pt, durata):    
    max = 0.2
    pt = (durata // 3) * pt + (pt if (durata % 3) >= 1.5 else 0)
    return max if pt > max else  float("{:.2f}".format(pt))

def punteggio_ogni_5_ore_max_06(pt, durata):    
    max = 0.6
    pt = (durata // 5) * pt + (pt if (durata % 3) >= 2.5 else 0)
    return max if pt > max else  float("{:.2f}".format(pt))

def punteggio_ogni_5_ore_max_05(pt, durata):    
    max = 0.5
    pt = (durata // 5) * pt + (pt if (durata % 3) >= 2.5 else 0)
    return max if pt > max else  float("{:.2f}".format(pt))

def punteggio_ogni_5_ore_max_04(pt, durata):    
    max = 0.4
    pt = (durata // 5) * pt + (pt if (durata % 3) >= 2.5 else 0)
    return max if pt > max else  float("{:.2f}".format(pt))