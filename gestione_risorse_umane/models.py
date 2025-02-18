import os
import re

from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from unical_template.models import TimeStampedModel, CreatedModifiedModel
from unical_template.utils import differenza_date_in_mesi_aru

from .decorators import is_apps_installed
from .peo_methods import PeoMethods


if 'csa' in settings.INSTALLED_APPS:
    from  csa.models import RUOLI
    from .csa_methods import CSAMethods as CareerMethods
else:
    from .career_methods import CareerMethods
    RUOLI = settings.RUOLI


class Avviso(TimeStampedModel):
    """
    Avvisi che se attivi vengono visualizzati in home page
    """
    titolo = models.CharField(max_length=255, blank=False, null=False,
                              help_text="Titolo Avviso")
    corpo_del_testo = models.TextField(help_text=("es. La partecipazione al Bando comporta..."),
                                       blank=False, null=False)
    ordinamento = models.PositiveIntegerField(help_text="posizione nell'ordinamento",
                                              blank=True, default=0)
    allegato = models.FileField(upload_to='allegati_avvisi/%m-%Y/',
                                null=True,blank=True)
    is_active = models.BooleanField('Visibile agli utenti', default=True)

    class Meta:
        ordering = ('ordinamento', )
        verbose_name = _('Avvisi')
        verbose_name_plural = _('Avvisi')

    def corpo_as_html(self):
        return text_as_html(self.corpo_del_testo)

    def __str__(self):
        return '{}'.format(self.titolo)


class TipoProfiloProfessionale(models.Model):
    """
    esempio
    Area Amministrativa-gestionale
    Area tecnica, tecnico-scientifica ed el. Dati
    Area Amministrativa
    """
    nome = models.CharField('Profilo professionale', max_length=255, blank=False, null=False,
                            help_text="")
    descrizione = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Tipo di Profilo Professionale')
        verbose_name_plural = _('Tipi di Profili Professionali')

    def __str__(self):
        return '{}'.format(self.nome)


class TipoContratto(models.Model):
    """
    es:
    Indeterminato
    Determinato
    """
    nome = models.CharField(max_length=255, blank=False, null=False,
                            help_text="")
    descrizione = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('Tipo di Contratto')
        verbose_name_plural = _('Tipi di Contratti')

    def __str__(self):
        return '{}'.format(self.nome)

class TipoInvalidita(models.Model):
    """
    es.
    P
    H
    descrivere meglio con colleghi ARU
    """
    nome = models.CharField(max_length=255, blank=False, null=False,
                            help_text="")
    identificativo = models.CharField(max_length=1, blank=False, null=False,
                            help_text="")
    descrizione = models.TextField(blank=True, default='')
    class Meta:
        verbose_name = _('Tipo di Invalidità')
        verbose_name_plural = _('Tipi di Invalidità')

    def __str__(self):
        return '{}'.format(self.nome)


class PosizioneEconomica(models.Model):
    nome = models.CharField('Categoria', max_length=255, blank=False, null=False,
                            help_text="Tradizionalmente: B, C, D o EP")
    punti_organico = models.FloatField(default=0.0)
    descrizione = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = _('Posizione Economica')
        verbose_name_plural = _('Posizioni Economiche')

    def __str__(self):
        return '{}'.format(self.nome)


class LivelloPosizioneEconomica(models.Model):
    posizione_economica = models.ForeignKey(PosizioneEconomica,
                                            on_delete=models.CASCADE,
                                            blank=True, null=True)
    nome = models.CharField('Livello Posizione Economica', max_length=255, blank=False, null=False,
                            help_text="Tradizionalmente: 1, 2, 3, 4, 5, 6 ma"
                                      " o qualsivoglia valore")
    class Meta:
        verbose_name = _('Livello Categoria')
        verbose_name_plural = _('Livelli Categoria')
        ordering = ('posizione_economica', 'nome')

    def get_descrizione(self):
        return self.posizione_economica.descrizione

    def get_categoria(self):
        return str(self)

    def __str__(self):
        return '{} {}'.format(self.posizione_economica,
                              self.nome)


class TitoloStudio(models.Model):
    nome = models.CharField(max_length=255, help_text=("Come da classificazione"
                                                       " ISTAT 2003-2011: "
                                                       "https://www.istat.it/it/files/2011/01/Classificazione-titoli-studio-28_ott_2005-classificazione_sintetica.xls" ))
    istituto = models.CharField(max_length=255, blank=False, default='')
    codice_livello = models.IntegerField(blank=True, default=0)
    codice_titolo_di_studio = models.IntegerField(blank=True, default=0)
    isced_97_level = models.CharField('Isced97 Level and Program destination',
                                      blank=True, default='',
                                      max_length=12)
    #isced_97_field = models.CharField('Isced97 Field of Study', blank=True, default='')
    descrizione = models.TextField()


    class Meta:
        ordering = ['nome',]
        verbose_name = _('Titolo di Studio')
        verbose_name_plural = _('Titoli di Studio')

    def __str__(self):
        return self.nome


class AfferenzaOrganizzativa(TimeStampedModel):
    """
    aff_org replicate da CSA
    """
    nome = models.CharField('Afferenza organizzativa', max_length=255, blank=False, null=False,
                            help_text="")
    descrizione = models.TextField(blank=True, default='')
    class Meta:
        ordering = ['nome',]
        verbose_name = _('Afferenza Organizzativa')
        verbose_name_plural = _('Afferenza Organizzative')

    def shortname(self):
        return re.sub(r'(?:\ -\ )|[\:,\.\ ]', '', self.nome[0:33].title())

    def __str__(self):
        return '{}'.format(self.nome)

def _ci_upload(instance, filename):
    """ this function has to return the location to upload the file """
    return os.path.join('dipendenti_unical/{}/carta_identita/{}'.format(  instance.matricola,
                                                         filename))

class Dipendente(TimeStampedModel, PeoMethods, CareerMethods):
    matricola = models.CharField(max_length=6, blank=False, null=False)
    utente = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.SET_NULL,
                               null=True, blank=True)
    nome = models.CharField(max_length=254, blank=True, default='')
    cognome = models.CharField(max_length=254, blank=True, default='')
    codice_fiscale = models.CharField(max_length=16, blank=True, default='')
    livello = models.ForeignKey(LivelloPosizioneEconomica,
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    disattivato = models.BooleanField(default=False,
                                      help_text="Se selezionato, "
                                                "esclude il dipendente "
                                                "da ogni operazione.")

    # sostituiti da csa
    profilo = models.ForeignKey(TipoProfiloProfessionale,
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    afferenza_organizzativa = models.ForeignKey(AfferenzaOrganizzativa,
                                               null=True, blank=True,
                                               on_delete=models.SET_NULL)
    sede = models.CharField(max_length=254,
                            blank=True, null=True, default='')
    invalidita = models.ForeignKey(TipoInvalidita,
                                  on_delete=models.SET_NULL,
                                  null=True, blank=True)
    # contratto = models.ForeignKey(TipoContratto,
                                  # on_delete=models.SET_NULL,
                                  # null=True, blank=True)
    ruolo = models.CharField(max_length=33,
                             blank=True, default='',
                             choices=RUOLI)
    data_presa_servizio =  models.DateField('Data presa servizio (CSA)',
                                            null=True, blank=True)
    data_cessazione_contratto = models.DateField('Data cessazione contratto (CSA)',
                                                 null=True,blank=True)
    data_ultima_progressione = models.DateField('Data ultima progressione calcolata (CSA)',
                                                null=True, blank=True)                                                 


    data_presa_servizio_manuale = models.DateField(null=True, blank=True)
    data_ultima_progressione_manuale = models.DateField(null=True, blank=True)
    data_cessazione_contratto_manuale = models.DateField(null=True, blank=True)


    motivo_cessazione_contratto = models.CharField(max_length=254,
                                                   blank=True, default='')
    carta_identita_front = models.FileField(upload_to=_ci_upload,
                                            null=True,blank=True)
    carta_identita_retro = models.FileField(upload_to=_ci_upload,
                                            null=True,blank=True)
    descrizione = models.TextField(blank=True, default='')
    data_ultima_sincronizzazione = models.DateTimeField(null=True,blank=True)

    class Meta:
        ordering = ['cognome',]
        verbose_name = _('Dipendente')
        verbose_name_plural = _('Dipendenti')

    def get_anzianita_mesi(self):
        """
        torna l'anzianità di servizio in mesi
        """
        presa_servizio = self.get_data_presa_servizio_csa()
        if not self.data_presa_servizio: return False
        return differenza_date_in_mesi_aru(presa_servizio)

    def get_anzianita(self):
        """
        torna tupla (anni, mesi)
        """
        anzianita_mesi = self.get_anzianita_mesi()
        if not anzianita_mesi: return False
        anni = int(anzianita_mesi/12)
        mesi = anzianita_mesi % 12
        return (anni, mesi)

    def get_anzianita_repr(self):
        """
        torna l'anzianità di servizio in mesi
        """
        anzianita = self.get_anzianita()
        if anzianita:
            return '{} anni e {} mesi'.format(*anzianita)
        return ''

    def __str__(self):
        return '{} - {} {}'.format(self.matricola,
                                   self.nome,
                                   self.cognome)


class FormazioneDipendente(TimeStampedModel):
    """
    """
    matricola = models.CharField(max_length=6, blank=False, null=False)
        
    dipendente = models.ForeignKey(Dipendente, on_delete=models.CASCADE, null=True, blank=True)

    partecipante = models.CharField(max_length=254, blank=True, default='', help_text="Valore letto in fase di importazione")
    
    evento_formativo = models.CharField(max_length=255, blank=False, null=False,
                              help_text="Evento formativo")

    ente_organizzatore = models.CharField(max_length=255, blank=False, null=False,
                              help_text="Ente organizzatore")

    data_inizio = models.DateField(null=True, blank=True)
    data_fine = models.DateField(null=True, blank=True)

    #durata_ore = models.FloatField(default=0.0)
    durata_ore = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, null=True, blank=False)

    ordinamento = models.PositiveIntegerField(help_text="posizione nell'ordinamento",
                                              blank=True, default=0)    
    is_active = models.BooleanField('Attivo', default=True)

    class Meta:
        ordering = ('ordinamento', )
        verbose_name = _('Formazione dipendente')
        verbose_name_plural = _('Formazione dipendenti')

    def __str__(self):
        return '({}) {}'.format(self.evento_formativo, self.ente_organizzatore)

class FunzioneNomina(TimeStampedModel):
    """
    """
    funzione = models.CharField(max_length=7, blank=False, null=False)
    descr = models.CharField(max_length=100, blank=False, null=False)
    #codice indentificativo di un raggruppamento di indici (comune a più bandi)
    id_code = models.CharField('Codice identificativo', max_length=33, blank=True,
                            null=True,
                            help_text='Lettera, numero o sequenza')

    class Meta:        
        verbose_name = _('Nomina nella funzione')
        verbose_name_plural = _('Nomina nelle funzioni')

    def __str__(self):
        return '({}) {} {}'.format(self.funzione, self.descr, self.id_code if self.id_code else '')

class PrestazioneIndividuale(TimeStampedModel):
    """
    """
    matricola = models.CharField(max_length=6, blank=False, null=False, primary_key=True)
        
    dipendente = models.ForeignKey(Dipendente, on_delete=models.CASCADE, null=True, blank=True)

    partecipante = models.CharField(max_length=254, blank=True, default='', help_text="Valore letto in fase di importazione")

    valutazione = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, null=True, blank=False)

    punteggio_finale = models.PositiveIntegerField(help_text="punteggio",
                                              blank=True, default=0)   

    ordinamento = models.PositiveIntegerField(help_text="posizione nell'ordinamento",
                                              blank=True, default=0)   

    is_active = models.BooleanField('Attivo', default=True)

    class Meta:        
        verbose_name = _('Prestazione individuale')
        verbose_name_plural = _('Prestazioni individuali')

    def __str__(self):
        return '({}) {} {}'.format(self.matricola, self.partecipante, self.punteggio_finale)