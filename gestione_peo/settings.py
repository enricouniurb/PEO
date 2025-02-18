from django.utils.translation import ugettext_lazy as _

NUMERAZIONI_CONSENTITE = [
                            #'Protocollo',
                            'Decreto o nota Rettorale (D.R.)',
                            'Decreto o nota del Direttore Generale (D.D.G.)',
                            'Decreto o nota del Direttore Dipartimento o Dirigente Struttura',
                            #'Decreto del Direttore del Centro Residenziale (D.CR.)',
                            #'Decreto del Prorettore (Centro Residenziale)',
                            'Delibera di Dipartimento/Facoltà',
                            #'Delibera del Senato',
                            #'Delibera del C.D.A.',
                         ]
#(codice, descrizione, tipo_doc)
CLASSIFICATION_LIST = (#('protocollo', _('Protocollo')),
                       ('decreto_rettorale', _('Decreto Rettorale (D.R.)'),['003'],'Rettore'), #,['003']
                       ('decreto_direttore_generale', _('Decreto o nota del Direttore Generale (D.D.G.)'), ['071','808','066'],'Direttore Generale'), #, ['071','808']
                       ('decreto_dirigente_struttura', _('Decreto o nota del Direttore Dipartimento o Dirigente Struttura'), ['827','010'],'Direttore di Dipartimento'), #, ['827','010']
                       #('decreto_direttore_cr', _('Decreto del Direttore del Centro Residenziale (D.CR.)')),
                       #('decreto_prorettore', _('Decreto del Prorettore (Centro Residenziale)')),
                       ('delibera_dipartimento_facolta', _('Delibera di Dipartimento/Facoltà'),['091'],'Consiglio di Dipartimento')) #,['091']
                       #('delibera_senato', _('Delibera del Senato')),
                       #('delibera_cda', _('Delibera del C.D.A.')))

# Campo testo "Etichetta" di default, creato automaticamente in ogni form
# di inserimento. Serve per l'individuazione rapida del modulo
# inserito da parte dell'utente ('id' e 'label' del field)
ETICHETTA_INSERIMENTI_ID = 'etichetta_inserimento'
ETICHETTA_INSERIMENTI_LABEL = 'Etichetta dell\'inserimento'
ETICHETTA_INSERIMENTI_HELP_TEXT = ('Il nome che desideri dare a questo modello compilato,'
                                   ' per individuarlo velocemente nella tua domanda')

COMPLETE_EMAIL_SENDER = 'peo-noreply@uniurb.it'
COMPLETE_EMAIL_SUBJECT = "{}, domanda trasmessa"
COMPLETE_EMAIL_BODY = """Caro {dipendente},

La tua domanda {bando} è stata correttamente trasmessa.
Per visionare il riepilogo di questa puoi collegarti al seguente url:

{url}{domanda_url}

Ti ricordiamo che attraverso la piattaforma sarà possibile
riaprire la domanda e ritrasmetterla fino alla data
di scadenza del bando.
"""

MOTIVAZIONE_DISABILITAZIONE_DUPLICAZIONE = "Disabilitazione per duplicazione in ({}) {}"
LOG_DUPLICAZIONE_MESSAGE = "Inserimento {origine} disabilitato e duplicato nella destinazione {destinazione}"
