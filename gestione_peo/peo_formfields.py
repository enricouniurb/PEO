import datetime
import os

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms import ModelChoiceField
from django.forms.fields import *
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import gettext as _

from django_form_builder.dynamic_fields import *
from django_form_builder.utils import _successivo_ad_oggi
from gestione_risorse_umane.models import Dipendente, TitoloStudio

from .settings import NUMERAZIONI_CONSENTITE, CLASSIFICATION_LIST


def _inizio_validita_titoli(bando, ultima_progressione):
    """
    Torna 'inizio_validita_titoli' del bando a cui la domanda
    si riferisce
    """
    data_inizio_validita = bando.data_validita_titoli_inizio
    if data_inizio_validita:
        if not ultima_progressione: return data_inizio_validita
        if bando.considera_ultima_progressione:
            if data_inizio_validita <= ultima_progressione:
                return ultima_progressione
        return data_inizio_validita
    return ultima_progressione


def _inizio_validita_titoli(bando, ultima_progressione):
    """
    Torna 'inizio_validita_titoli' del bando a cui la domanda
    si riferisce
    """
    data_inizio_validita = bando.data_validita_titoli_inizio
    if data_inizio_validita:
        if not ultima_progressione: return data_inizio_validita
        if bando.considera_ultima_progressione:
            if data_inizio_validita <= ultima_progressione:
                return ultima_progressione
        return data_inizio_validita
    return ultima_progressione


def _limite_validita_titoli(domanda_bando):
    """
    Torna 'limite_validita_titoli' del bando a cui la domanda
    si riferisce
    """
    bando = domanda_bando.bando
    return bando.data_validita_titoli_fine


def _get_livello_dipendente(domanda_bando):
    return domanda_bando.get_livello_dipendente()


def _ultima_progressione_data_presa_servizio(domanda_bando):
    """
    Torna una tuplua con 'data_ultima_progressione' e
    'data_presa_servizio' del dipendente che ha creato la domanda
    """
    dipendente = domanda_bando.dipendente
    bando = domanda_bando.bando

    data_presa_servizio = domanda_bando.get_presa_servizio_dipendente()
    ultima_progressione = domanda_bando.get_ultima_progressione_dipendente()

    # OVERRIDE delle date progressione e presa_servizio SE queste sono
    # maggiori di bando.ultima_progressione SE E SOLO SE il dipendente
    # risulta essere stato abilitato a partecipare da ARU.
    # Questo evita che incoerenze delle interpretazioni di carriera lato CSA
    # confliggano con la decisione di ARU di abilitare un dipendente
    # alla partecipazione. Questo consente di inserire titoli relativi
    # ad un delta tra bando.ultima_progressione e
    # bando.data_validita_titoli_fine.
    # Se il dipendente dovesse in aggiunta inserire ulteriori pregressi
    # li dovrebbe innanzitutto intervenire ARU sui dati presenti in CSA
    # if dipendente.idoneita_peo_attivata():
        # if ultima_progressione > bando.ultima_progressione:
            # ultima_progressione = bando.ultima_progressione
        # if data_presa_servizio > bando.ultima_progressione:
            # data_presa_servizio = bando.ultima_progressione
    # Questo risolve i conflitti che potrebbero incorrere
    # tra una decisione di ARU e il comportamento del sistema
    return (ultima_progressione, data_presa_servizio)


# 'type':'date', <- confligge con datepicker che serve solo per ie11
_date_field_options = {'class': 'datepicker'}


class PEO_BaseDateField(BaseDateField):
    """
    DateField
    """
    widget = forms.DateInput(attrs=_date_field_options)


class PEO_BaseDateTimeField(BaseDateTimeField):
    """
    DateTimeField
    """
    widget = forms.DateInput(attrs=_date_field_options)


class PEO_PunteggioFloatField(PositiveFloatField):
    """
    Punteggio come FloatField positivo
    """
    field_type = _("_PEO_  Punteggio (numero con virgola)")
    name = "punteggio_dyn"

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

    def define_value(self, custom_value, **kwargs):
        """
        Se DescrizioneIndicatore o Indicatore Ponderato prevedono
        un punteggio massimo, applica un validatore MaxValueValidator
        """
        domanda_bando = kwargs.get('domanda_bando')
        descrizione_indicatore = kwargs.get('descrizione_indicatore')
        if domanda_bando:
            posizione_economica = _get_livello_dipendente(domanda_bando).posizione_economica
            p_max = descrizione_indicatore. \
                get_pmax_pos_eco(posizione_economica)
            if not p_max:
                p_max = descrizione_indicatore.indicatore_ponderato. \
                    get_pmax_pos_eco(posizione_economica)
            if p_max:
                self.validators.append(MaxValueValidator(p_max))


class PEO_TitoloStudioField(ModelChoiceField, BaseCustomField):
    """
    SelectBox con i titoli di studio
    """
    field_type = _("_PEO_  Titoli di studio")
    name = "titolo_di_studio_superiore"

    def __init__(self, **data_kwargs):
        # Di default, inserisce tutti i titoli di studio definiti
        data_kwargs['queryset'] = TitoloStudio.objects.all()
        super().__init__(**data_kwargs)

    def define_value(self, custom_value, **kwargs):
        """
        Se per la categoria economica del Dipendente alcuni titoli
        di studio sono inibiti, li elimina dalla queryset
        """
        domanda_bando = kwargs.get('domanda_bando')
        descrizione_indicatore = kwargs.get('descrizione_indicatore')
        if domanda_bando:
            pos_eco = _get_livello_dipendente(domanda_bando).posizione_economica
            punteggio_titoli = domanda_bando.bando. \
                               get_punteggio_titoli_pos_eco(pos_eco)
            if punteggio_titoli:
                self.queryset = punteggio_titoli
            else:
                self.queryset = TitoloStudio.objects.none()


class PEO_SubDescrizioneIndicatoreField(ModelChoiceField, BaseCustomField):
    """
    SelectBox con le sotto-categorie SubDescrizioneIndicatore
    """
    field_type = _("_PEO_  Selezione sotto-categorie DescrizioneIndicatore")
    name = 'sub_descrizione_indicatore'

    def __init__(self, **data_kwargs):
        # Di default, inserisce tutti i SubDescrizioneIndicatore
        sub_descr_ind = apps.get_model('gestione_peo',
                                       'SubDescrizioneIndicatore')
        data_kwargs['queryset'] = sub_descr_ind.objects.all()
        super().__init__(**data_kwargs)

    def define_value(self, custom_value,**kwargs):
        """
        Se la DescrizioneIndicatore associata al Form prevede SubDescrInd
        li sostituisce ai valori di default
        """
        domanda_bando = kwargs.get('domanda_bando')
        descrizione_indicatore = kwargs.get('descrizione_indicatore')
        sub_descr_ind = None
        if descrizione_indicatore:
            sub_descr_ind = descrizione_indicatore. \
                            subdescrizioneindicatore_set.all()           
        if sub_descr_ind:
            self.queryset = sub_descr_ind
        
   
             
class PEO_SubDescrizioneIndicatoreFormField(ModelChoiceField, BaseCustomField):
    """
    SelectBox con le sotto-categorie SubDescrizioneIndicatore
    """
    field_type = _("_PEO_  Selezione sotto-categorie con form DescrizioneIndicatore")
    name = 'sub_descrizione_indicatore_form'
    is_complex = True
    sub_forms = []

    def __init__(self, **data_kwargs):
        # Di default, inserisce tutti i SubDescrizioneIndicatore
        sub_descr_ind = apps.get_model('gestione_peo',
                                       'SubDescrizioneIndicatore')
        data_kwargs['queryset'] = sub_descr_ind.objects.all()
        super().__init__(**data_kwargs)

    def define_value(self, custom_value,**kwargs):
        """
        Se la DescrizioneIndicatore associata al Form prevede SubDescrInd
        li sostituisce ai valori di default
        """
        domanda_bando = kwargs.get('domanda_bando')
        descrizione_indicatore = kwargs.get('descrizione_indicatore')
        sub_descr_ind = None
        if descrizione_indicatore:
            kwargs['subdescrizioneindicatoreformfield']= True
            sub_descr_ind = descrizione_indicatore. \
                            subdescrizioneindicatore_set.all()
            self.sub_forms = [sub.get_form(**kwargs) for sub in sub_descr_ind]

        if sub_descr_ind:
            self.queryset = sub_descr_ind
        

    def get_fields(self):        
        ereditati = super().get_fields()        
        for sub_form in self.sub_forms:
            if sub_form:
                for key, field in sub_form.fields.items():
                    field.name = '{}_submulti_{}'.format(key,sub_form.descrizione_indicatore.id)
                    classes = field.widget.attrs.get("class")                     
                    field.widget.attrs.update({'class': ('{} '.format(classes) if classes else '') + 'submulti submulti_{}'.format(sub_form.descrizione_indicatore.id)})           

                #filtered_dict = {k:v for (k,v) in d.items() if filter_string != 'etichetta_inserimento'}.values()
                ereditati.extend(sub_form.fields.values())
        return ereditati

class PEO_DateStartEndComplexField(DateStartEndComplexField):
    """
    Field composto da DataInizio (DateField) e DataFine (DateField)
    """
    field_type = _("_PEO_ Data inizio e Data fine")
    is_complex = True

    def __init__(self, *args, **data_kwargs):
        # Data Inizio
        self.start = PEO_BaseDateField(*args, **data_kwargs)
        self.start.required = True
        self.start.label = _('Data Inizio')
        self.start.name = "data_inizio_dyn"

        # Riferimento a DateStartEndComplexField
        self.start.parent = self

        # Data Fine
        self.end = PEO_BaseDateField(*args, **data_kwargs)
        self.end.required = True
        self.end.label = _('Data Fine')
        self.end.name = "data_fine_dyn"

        # Riferimento a DateStartEndComplexField
        self.end.parent = self


class PEO_DateInRangeComplexField(PEO_DateStartEndComplexField):
    """
    Field composto da DataInizio (DateField) e DataFine (DateField)
    che deve rigorisamente ricadere nel range imposto dal Bando
    (Data PresaServizio/UltimaProgressione - LimiteTitoli Bando)
    """
    field_type = _("_PEO_  Data inizio e Data fine IN RANGE of bando")
    is_complex = True

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

        # Definizione 'name' dei field Inizio e Fine
        # Tutti gli altri parametri sono inizializzati tramite il super
        self.start.name = 'data_inizio_dyn_inner'
        self.end.name = 'data_fine_dyn_inner'

    def get_start_name(self):
        return self.start.name

    def get_end_name(self):
        return self.end.name

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo complesso deve attenersi strettamente ai vincoli
        imposti dal bando, per cui, oltre a ereditard i controlli standard
        del parent, si eseguono ulteriori verifiche
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []

        ultima_progressione = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[0]
        data_presa_servizio = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        inizio_validita_titoli = _inizio_validita_titoli(domanda_bando.bando,
                                                         ultima_progressione)
        limite_validita_titoli = _limite_validita_titoli(domanda_bando)

        errors = []
        # Recupero la lista di errori proveniente dai controlli del super
        errors = errors + (super().raise_error(name,
                                               cleaned_data,
                                               **kwargs))

        value = cleaned_data.get(name)

        # Se il campo non viene correttamente inizializzato
        if not value:
            return []

        # Si valuta 'Data Inizio'
        if name == self.start.name:
            # Se la data di inizio è successiva al limite imposto dal bando
            if value > limite_validita_titoli:
                errors.append("La data di inizio non può"
                              " essere successiva al"
                              " {}".format(limite_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
            # Se la data di inizio è precedente alla presa di servizio
            if value < data_presa_servizio:
                errors.append("La data di inizio non può essere precedente"
                              " alla presa di servizio:"
                              " {}".format(data_presa_servizio.strftime(settings.STRFTIME_DATE_FORMAT)))

            # Check con Field Protocollo se presente
            protocollo = PEO_ProtocolloField()
            data_protocollo_name = protocollo.get_data_name()
            data_protocollo = cleaned_data.get(data_protocollo_name)

            # Se nel form è presente il protocollo
            # e la data di inizio è precedente a quella di protocollo
            if data_protocollo and value < data_protocollo:
                errors.append("La data di inizio non può essere"
                              " precedente alla data del protocollo")
        # Si valuta 'Data Fine'
        elif name == self.end.name:
            # Se la data di fine è precedente all'ultima progressione
            # o al limite imposto dal bando
            if value < inizio_validita_titoli:
                errors.append("La data di fine è precedente alla data:"
                              " {}".format(inizio_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
        return errors


class PEO_DateInRangeInCorsoComplexField(PEO_DateInRangeComplexField):
    """
    Field composto da DataInizio (DateField), DataFine (DateField)
    e In Corso (BooleanField).
    Rispetta i vincoli del parent DateInRangeComplexField
    ma offre la possibilità di non specificare la data di fine (in corso)
    """
    field_type = _("_PEO_  Data inizio e Data fine IN RANGE of bando + 'In corso'")
    is_complex = True

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

        self.end.required = False

        # BooleanField aggiuntivo
        self.in_corso = CheckBoxField(**data_kwargs)
        self.in_corso.required = False
        self.in_corso.widget = forms.CheckboxInput()
        self.in_corso.label = 'In corso'
        self.in_corso.name = 'in_corso_dyn'
        self.in_corso.parent = self

    def get_in_corso_name(self):
        return self.in_corso.name

    def get_fields(self):
        ereditati = super().get_fields()
        ereditati.extend([self.in_corso])
        return ereditati

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo complesso dete attenersi strettamente ai vincoli
        imposti dal bando, per cui, oltre a ereditard i controlli standard
        del parent, si eseguono ulteriori verifiche
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []
        # limite_validita_titoli = _limite_validita_titoli(domanda_bando)
        # ultima_progressione = \
            # _ultima_progressione_data_presa_servizio(domanda_bando)[0]
        # data_presa_servizio = \
            # _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        errors = []

        value = cleaned_data.get(name)
        end_value = cleaned_data.get(self.end.name)
        # Si valuta 'In corso'
        if name == self.in_corso.name:
            # Se è definito anche Data Fine
            if value and end_value:
                errors.append("Compilare solo uno dei campi"
                              " 'Data Fine' e 'Incarico in corso'")
            # Se non è definito nè In Corso nè Data Fine
            if not value and not end_value:
                errors.append("Compilare almeno uno dei campi"
                              " 'Data Fine' e 'Incarico in corso'")
        # Se valuto gli altri fields recupero gli altri errori
        else:
            errors = errors + (super().raise_error(name,
                                                   cleaned_data,
                                                   **kwargs))
        return errors


class PEO_DateOutOfRangeComplexField(PEO_DateStartEndComplexField):
    """
    Field composto da DataInizio (DateField) e DataFine (DateField)
    che deve rigorisamente ricadere fuori dal range imposto dal Bando
    (Data PresaServizio/UltimaProgressione - LimiteTitoli Bando)
    """
    field_type = _("_PEO_  Data inizio e Data fine OUT OF RANGE of bando")
    is_complex = True

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

        self.start.name = 'data_inizio_dyn_out'
        self.end.name = 'data_fine_dyn_out'

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo complesso deve attenersi strettamente ai vincoli
        imposti dal bando, per cui, oltre a ereditard i controlli standard
        del parent, si eseguono ulteriori verifiche
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []
        data_presa_servizio = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        errors = []
        errors = errors + (super().raise_error(name,
                                               cleaned_data,
                                               **kwargs))

        value = cleaned_data.get(name)

        if not value:
            return []

        # Si valuta 'Data Inizio'
        if name == self.start.name:
            # Se la data di inizio è successiva alla presa di servizio
            if value > data_presa_servizio:                
                errors.append("La data di inizio non può essere successiva "
                              "alla presa di servizio: "
                              "{}".format(data_presa_servizio.strftime(settings.STRFTIME_DATE_FORMAT)))
        # Si valuta 'Data Fine'
        elif name == self.end.name:
            # Se la data di fine è successiva alla presa di servizio
            if value > data_presa_servizio:
                errors.append("La data di fine non può essere successiva "
                              "alla presa di servizio: "
                              "{}".format(data_presa_servizio.strftime(settings.STRFTIME_DATE_FORMAT)))
        return errors


class PEO_DataLowerThanBandoField(PEO_BaseDateField):
    """
    DateField singolo all'interno dei limiti imposti dal bando
    """
    field_type = _("_PEO_  Data singola IN RANGE of bando")

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo deve rispettare i vincoli temporali del bando
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []
        ultima_progressione = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[0]
        data_presa_servizio = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        inizio_validita_titoli = _inizio_validita_titoli(domanda_bando.bando,
                                                         ultima_progressione)
        limite_validita_titoli = _limite_validita_titoli(domanda_bando)

        if inizio_validita_titoli == data_presa_servizio:
            inizio_validita_titoli = False

        errors = []
        value = cleaned_data

        if not value:
            return ['Valore non presente']

        # Se la data è successiva al termine imposto dal bando
        if value > limite_validita_titoli:
            errors.append("La data non può essere successiva "
                          "al limite imposto dal bando: "
                          "{}".format(limite_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
        # Se la data è precedente a inizio_validita_titoli
        if inizio_validita_titoli and value < inizio_validita_titoli:
            errors.append("La data non può essere precedente"
                          " a: {}".format(inizio_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
        # Se la data è precedente all'ultima progressione
        # elif ultima_progressione and (value < ultima_progressione):
            # errors.append("La data non può essere precedente all'ultima "
                          # "progressione effettuata: {} "
                          # .format(ultima_progressione))
        # Se la data è precedente alla presa di servizio
        if value < data_presa_servizio:
            errors.append("La data non può essere precedente alla presa "
                          "di servizio: {}".format(data_presa_servizio.strftime(settings.STRFTIME_DATE_FORMAT)))
        return errors


class PEO_AnnoInRangeOfCarrieraField(PositiveIntegerField):
    """
    Intero positivo per rappresentare un anno all'interno dei limiti
    temporali imposti dal bando
    """
    field_type = _("_PEO_  Anno singolo IN RANGE of bando")

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)

    def raise_error(self, name, cleaned_data ,**kwargs):
        """
        L'anno rappresentato, oltre alle validazioni su PositiveInteger,
        deve rispettare i limiti imposti dal bando e dalla carriera
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []
        ultima_progressione = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[0]
        data_presa_servizio = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        inizio_validita_titoli = _inizio_validita_titoli(domanda_bando.bando,
                                                         ultima_progressione)
        limite_validita_titoli = _limite_validita_titoli(domanda_bando)

        if inizio_validita_titoli == data_presa_servizio:
            inizio_validita_titoli = False

        errors = []
        # value = cleaned_data.get(name)
        value = cleaned_data

        if not value:
            return ["Specificare un valore valido"]

        # Se è successivo all'anno di 'limite_validita_titoli' del bando
        if value > limite_validita_titoli.year:
            errors.append("Questo anno non può essere superiore a "
                          "quello della data limite imposta dal bando: "
                          "{}".format(limite_validita_titoli.year))

        # Se è precedente a inizio_validita_titoli
        if inizio_validita_titoli and value < inizio_validita_titoli.year:
                errors.append("Questo anno non può essere precedente a "
                              "{}".format(inizio_validita_titoli.year))
        # Se è successivo all'anno dell'ultima progressione
        # elif ultima_progressione and (value < ultima_progressione.year):
            # errors.append("Questo anno non può essere precedente a "
                          # "quello dell'ultima progressione effettuata: "
                          # "{}".format(ultima_progressione.year))

        # Se è precedente all'anno della presa di servizio
        if value < data_presa_servizio.year:
            errors.append("Questo anno non può essere precedente a "
                          "quello della presa di servizio: "
                          "{}".format(data_presa_servizio.year))
        return errors


class PEO_ProtocolloField(ProtocolloField):
    field_type = _("_PEO_  Protocollo (tipo/numero/data)")
    is_complex = True

    def __init__(self, **data_kwargs):
        super().__init__(**data_kwargs)
        self.data.widget = forms.DateInput(attrs=_date_field_options)
        self.tipo.label = _("Tipo atto")
        self.tipo.help_text = _("Scegli il tipo atto, "
                                "al quale la numerazione è riferita")
        self.numero.label = _("Numero Delibera o Decreto")
        self.numero.help_text = _("Indica il numero del "
                                  "decreto o delibera")
        self.data.label = _("Data Delibera o Decreto")
        self.data.help_text = _("Indica la data del decreto o delibera")
        self.tipo.choices = [('', 'Scegli una opzione')]
        self.tipo.choices += [(i[0].lower().replace(' ', '_'), i[1]) \
                             for i in CLASSIFICATION_LIST]

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo complesso subisce controlli inerenti i parametri
        imposti dal bando e allo stesso tempo si relaziona, se presente,
        a DataInizio e DataFine in range
        """
        domanda_bando = kwargs.get('domanda_bando')
        if not domanda_bando: return []
        ultima_progressione = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[0]
        data_presa_servizio = \
            _ultima_progressione_data_presa_servizio(domanda_bando)[1]

        inizio_validita_titoli = _inizio_validita_titoli(domanda_bando.bando,
                                                         ultima_progressione)
        limite_validita_titoli = _limite_validita_titoli(domanda_bando)

        if inizio_validita_titoli == data_presa_servizio:
            inizio_validita_titoli = False

        value = cleaned_data.get(name)

        if not value:
            return ["Valore mancante"]

        # Si valuta 'Data protocollo'
        if name == self.data.name:
            errors = []
            # Se la data è successiva al limite imposto dal bando
            if value > limite_validita_titoli:
                errors.append("La data di protocollo non può "
                              "essere successiva al "
                              "{}".format(limite_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
            # Se la data è successiva ad oggi
            if _successivo_ad_oggi(value):
                errors.append("La data di protocollo non può essere "
                              "successiva ad oggi")
            # Se la data è precedente alla presa di servizio
            if value < data_presa_servizio:
                errors.append("La data di protocollo non può essere "
                              "precedente alla presa di servizio: "
                              "{}".format(data_presa_servizio.strftime(settings.STRFTIME_DATE_FORMAT)))

            # Serve interfacciarsi con DateInRangeInCorsoComplexField
            d = PEO_DateInRangeInCorsoComplexField()

            in_corso_name = d.get_in_corso_name()
            in_corso = cleaned_data.get(in_corso_name)

            data_fine_name = d.get_end_name()
            data_fine = cleaned_data.get(data_fine_name)

            data_inizio_name = d.get_start_name()
            data_inizio = cleaned_data.get(data_inizio_name)

            # Se NON è stato checkato il campo "fino_ad_oggi"
            # e la data di fine è precedente all'ultima progressione,
            # l'incarico non è continuativo
            if not in_corso and inizio_validita_titoli:
                if data_fine and data_fine < inizio_validita_titoli:
                    if value < inizio_validita_titoli:
                        errors.append("La data del protocollo "
                                      "è precedente alla data: "
                                      "{}".format(inizio_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))

            # Se non esistono i campi Data allora non
            # siamo in grado di capire se l'incarico è di tipo continuativo,
            # per cui la data del protocollo deve essere sempre successiva
            # all'ultima progressione effettuata, a meno che non sia
            # settata la data di inizio validità titoli
            if not data_inizio and inizio_validita_titoli:
                if value < inizio_validita_titoli:
                    errors.append("La data del protocollo è precedente "
                                  "alla data: {}".format(inizio_validita_titoli.strftime(settings.STRFTIME_DATE_FORMAT)))
            return errors


class PEO_URLField(CharField, BaseCustomField):
    """
    URL
    """
    field_type = _("URL")

    def __init__(self, *args, **data_kwargs):
        super().__init__(*args, **data_kwargs)
    
    def raise_error(self, name, cleaned_data, **kwargs):    
        if not cleaned_data: return []
        if not re.match('^(https?:)?[a-zA-Z0-9_.+-/#~]+$', str(cleaned_data)):
            return [_("Indirizzo link non valido"),]


class PEO_AllegatoURLField(BaseCustomField):
    """
    Allegato o URL al documento 
    """
    field_type = "_PEO_  Allegato o URL al documento"
    is_complex = True    

    def __init__(self, *args, **data_kwargs):
        # Allegato
        self.allegato = CustomFileField(*args, **data_kwargs)   
        self.allegato.name = "allegato"     
        self.allegato.label = _("Documento")                
        self.allegato.required = False
        self.allegato.parent = self

        # Url
        self.url_documento = PEO_URLField(*args, **data_kwargs)   
        self.url_documento.required = False
        self.url_documento.label = _("Indirizzo link al documento")
        self.url_documento.name = "url_documento"        
        self.url_documento.parent = self      

    def get_fields(self):
        return [self.url_documento, self.allegato]  

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Questo campo complesso richiede la compilazione o dell'allegato o del url
        """
        errors = []
        allegato_value = cleaned_data.get(self.allegato.name)

        allegati = kwargs.get('allegati')
        if (allegati and type(allegati) is dict):
            if (self.allegato.name in allegati):
                allegato_value = allegati.get(self.allegato.name)        
                        
        url_value = cleaned_data.get(self.url_documento.name)     
        if (url_value):
            errors = self.url_documento.raise_error(self.url_documento.name, url_value, **kwargs)
        if not allegato_value and not url_value: 
          errors.append("Si richiede di allegare il documento oppure inserire l'URL al documento")
        
        return errors


class DurataComePositiveFloatField(PositiveFloatField):
    """
    Durata come DecimalField positivo
    """
    field_type = _("Durata come numero decimale (anni,mesi,ore)")
    name = 'durata_come_decimale'

    def raise_error(self, name, cleaned_data, **kwargs):
        """
        Solo numeri (espressioni del tipo 16e50 non sono ammesse)
        """
        if not cleaned_data: return []
        if not re.match('^[0-9]+\.?[0-9]?[0-9]?$', str(cleaned_data)):
            return [_("Solo numeri ammessi"),]