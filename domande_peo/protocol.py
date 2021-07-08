# © 2020 Alessia Ventani <alessia.ventani@uniurb.it>

# SPDX-License-Identifier: GPL-3.0

import datetime
import io
import os
from typing import Type, Any

from requests import Session
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from zeep.transports import Transport
import base64
import logging.config
import xmltodict
import json
from zeep.xsd import SkipValue
from zeep import Client


PROT_DOC_ENCODING = 'utf-8'
PROT_MAX_LABEL_LENGHT = 99

# wildcard di oracle da evitare
PROT_UNALLOWED_CHARS = ['&', '(', ')', ',', '?', '!', '{', '}', '\\', '[', ']',
                        ':', '~', '|', '$', '<', '>', '*', '%',
                        ';', '"', "'"]

# codici classificazioni dei fascicoli speciali
SPECIAL_DOSSIER_CLASSIFICATION_CODE = {"studenti": "05/00",
                                          "personale": "07/00",
                                          "persona_giuridica": "10/00"}

def clear_string(word):
    if not isinstance(word, str): return word
    word = word[:PROT_MAX_LABEL_LENGHT]
    for c in PROT_UNALLOWED_CHARS:
        word = word.replace(c, '')
    return word


class WSTitulusClient(object):

    # documento
    _XML_DOCUMENT1 = """<?xml version="1.0" encoding="utf-16" ?>
    <doc anno="{year}" tipo="{type}" bozza="{draft}">
    <oggetto>{object}</oggetto>
    <classif cod="{classification_code}" xml:space="preserve">{classification_description}</classif>
    {attachments_descriptions}
    <rif_interni>  
    <rif_interno diritto="RPA" nome_persona="{internal_reference_name}" nome_uff="{internal_reference_office}"></rif_interno>
    </rif_interni>
    <rif_esterni>
    <rif_esterno>
    <nome cod="{external_reference_code}" xml:space="preserve">{external_reference_name}</nome>
    <referente cod="{external_reference_code}" nominativo="{external_reference_name}"/>
    </rif_esterno>
    </rif_esterni>
    </doc>"""

  # documento
    _XML_DOCUMENT = """<?xml version="1.0" encoding="utf-16" ?>
    <doc tipo="{type}" bozza="{draft}">
    <oggetto>{object}</oggetto>
    <classif cod="{classification_code}" xml:space="preserve"></classif>
    <allegato>0 - nessun allegato</allegato>
    <rif_interni>  
    <rif_interno diritto="RPA" nome_persona="{internal_reference_name}" nome_uff="{internal_reference_office}"></rif_interno>
    </rif_interni>
    <rif_esterni>
    <rif_esterno>
    <nome cod="{external_reference_code}" xml:space="preserve">{external_reference_name}</nome>
    </rif_esterno>
    </rif_esterni>
    </doc>"""


    # allegato
    _XML_ATTACHMENT = """<attachmentBeans>
                           <AttachmentBean>
                             <fileName>{name}</fileName>
                             <description>{description}</description>
                             <mimeType>{type}</mimeType>
                             <content>{fileContent}</content>
                           </AttachmentBean>
                       </attachmentBeans>
        """
    
    # fascicolo
    _XML_DOSSIER = """
                    <fascicolo anno="{year}">
                    <oggetto>{object}</oggetto>
                    <classif cod="{classif}"/>
                    <rif_interni>
                            <rif diritto="{right}" nome_persona="{person_name}" nome_uff="{office_name}"/>
                    </rif_interni>
                    </fascicolo>
    """
    # aggiunta di un documento in un fascicolo
    _XML_DOSSIER_IN_DOCUMENT = """<fascicolo physdoc="{dossier_physdoc}">
                                  <doc physdoc="{document_physdoc}"/>
                                </fascicolo>
    """

    # persona esterna (ACL)
    _XML_EXTERNAL_PERSON = """<persona_esterna nome="{name}" cognome="{surname}" codice_fiscale="{fiscal_code}">
    <recapito>
    <email addr="{email}"/>
    <email_certificata addr="{istitutional_email}"/>
    </recapito>
    </persona_esterna>"""

    REQUIRED_ATTRIBUTES = [
        "username",
        "password",
        "wsdl_url"
    ]

    saveParams = {
        'pdfConversion': False,
        'sendEMail': False
    }

    def __init__(self,
                 wsdl_url,
                 username,
                 password,
                 required_attributes=REQUIRED_ATTRIBUTES,
                 **kwargs):

        for attr in required_attributes:
            setattr(self, attr, clear_string(kwargs.get(attr)))

        self.username = username
        self.password = password
        self.wsdl_url = wsdl_url
        self.client = None
        self.clientACL = None
        self.login = None
        self.attachments  = []         # lista di allegati da aggiungere al documento da protocolre

    def _get_attachment_dict(self):
        return {'attachment_id': None,
                'name':        None,
                'description': None,
                'type':        None,
                'fileContent':        None}

    def start_connection(self):

        logging.config.dictConfig({
            'version': 1,
            'formatters': {
                'verbose': {
                    'format': '%(name)s: %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'zeep.transports': {
                    'level': 'DEBUG',
                    'propagate': True,
                    'handlers': ['console'],
                },
            }
        })

        session = Session()
        session.auth = HTTPBasicAuth(self.username, self.password)
        self.client = Client(wsdl=self.wsdl_url+"Titulus4?wsdl", transport=Transport(session=session))
        self.clientACL = Client(wsdl=self.wsdl_url+"Acl4?wsdl", transport=Transport(session=session))


    def check_connection(self):
        # controllo della connessione al web service
        if not(self.client and self.clientACL):
            self.start_connection()

    def _encode_filestream(self, fopen, enc=False):
        try:
          if enc:
            return fopen.read().encode(PROT_DOC_ENCODING)
          else:
            return fopen.read()
        except:
            return fopen


    def create_dossier(self, parameters, template=_XML_DOSSIER):                   # TODO: change on folder type 
        """Crea un nuovo protocollo

            Argomenti:
            parameters -- valori da inserire nel fascicolo
            template -- template per il fascicolo (default = _XML_DOSSIER)
        """
        if isinstance(template, str):
            template = template.format(**conf_fascicolo)
        else:
            template = template.decode(PROT_DOC_ENCODING).format(**parameters)
        print("Creating {}".format(template))
        return self.client.service.newFolder(template)

    # restituisce un dizionario con le informazioni del documento/fascicolo desiderato
    def search(self, filter):                                                   
        document =  self.client.service.search(filter, SkipValue, SkipValue)
        return json.loads(json.dumps(xmltodict.parse(document)))
    
    # rimuove tutti gli allegati
    def clear_attachments(self):
        self.attachments.clear()

    def add_attachment(self, name,
                                description,
                                fopen,
                                type='Allegato'):
        """
        name: deve essere con l'estenzione esempio: .pdf altrimenti errore xml -201!
        il fopen popola la lista degli allegati.
        """
        if len(name.split('.')) == 1:
            raise Exception(("'name' deve essere con l'estensione "
                             "esempio: .pdf altrimenti errore xml -201!"))
        self.check_connection()

        attachment_idsum = 2

        for al in self.attachments:
            al['attachment_id'] = self.attachments.index(al) + attachment_idsum

        attachment_dict = self._get_attachment_dict()
        attachment_dict['attachment_id'] = len(self.attachments) + attachment_idsum
        attachment_dict['name'] = clear_string(name)
        attachment_dict['description'] = clear_string(description)
        attachment_dict['type'] = clear_string(type)
        attachment_dict['fileContent'] = self._encode_filestream(fopen)
        attachment = ""

        # gestione eccezione ns0 e ns0
        try: 
          attachment = self.client.wsdl.types.get_type('ns2:AttachmentBean')() # ns0 o ns2?
        except:
          attachment = self.client.wsdl.types.get_type('ns0:AttachmentBean')() # ns0 o ns2?
 
        attachment.id = len(self.attachments) + attachment_idsum
        attachment.fileName = clear_string(name)
        attachment.fileContent = attachment_dict['fileContent']
        attachment.mimeType = type
        attachment_dict['AttachmentBean'] = attachment

        self.attachments.append(attachment_dict)
        return self._XML_ATTACHMENT.format(**attachment_dict)

    def protocol(self, protocol_parameters, force=False, template=_XML_DOCUMENT):
        """
        Se "force" è disabilitato non sarà possibile protocolre un
        documento già protocolto.
        Se force è abilitato riprotocol il documento e aggiorna il numero
        Torna un dizionario come segue:
        {'annoProt': 2018,
         'annoProtUff': 0,
         'dataProt': None,
         'error_description': None,
         'error_number': 0,
         'numProt': 183,
         'numProtUff': 0,
         'siglaUff': None}
        """

        self.check_connection()

        # popolo la lista degli allegati se presenti
        if self.attachments:
          attachment_list = []
          for attachment in self.attachments:
             try:
              attachmentBean_object = self.client.type_factory('ns2').AttachmentBean(
                  fileName=attachment['AttachmentBean']['fileName'], 
                  mimeType=attachment['AttachmentBean']['mimeType'], 
                  content=attachment['AttachmentBean']['fileContent'] )
             except:
               attachmentBean_object = self.client.type_factory('ns0').AttachmentBean(fileName=attachment['AttachmentBean']['fileName'], mimeType=attachment['AttachmentBean']['mimeType'], content=attachment['AttachmentBean']['fileContent'] )
             attachment_list.append(attachmentBean_object) 
          try:
            attachmentBean_type = self.client.type_factory('ns0').ArrayOf_tns1_AttachmentBean(attachment_list)
          except:
            attachmentBean_type = self.client.type_factory('ns2').ArrayOf_tns1_AttachmentBean(attachment_list) 

        else:
          attachmentBean_type = SkipValue
        prot = self.client.service.saveDocument(template.format(**protocol_parameters), attachmentBean_type, self.saveParams)
        prot_dict = json.loads(json.dumps(xmltodict.parse(prot['_value_1'])))
        #numero = prot_dict['Response']['Document']['@physdoc']
        #anno = prot_dict['Response']['Document']['doc']['@anno']
        return prot_dict
    
    def search_in_acl(self, filter):
        return self.clientACL.service.search(filter, SkipValue, SkipValue)

    # aggiunge anagrafica esterna e ritorna il numero di matricola
    def add_external_person(self, parameters, template=_XML_EXTERNAL_PERSON):
        esternal_person = self.clientACL.service.addExternalUser(template.format(**parameters))
        return json.loads(json.dumps(xmltodict.parse(esternal_person['_value_1'])))['Response']['Document']['persona_esterna']['@matricola']

    def attachment_descriptions(self, description_list):
        return "\n".join(["<allegato>"+description+"</allegato>" for description in description_list])

    # funzione per cercare un fascicolo
    def search_special_dossier(self, classification, filter):
        dossier = self.client.service.search("([fasc_classifcod]="+SPECIAL_DOSSIER_CLASSIFICATION_CODE[classification]+") AND ("+filter+")", SkipValue, SkipValue)
        try: 
            id_dossier = json.loads(json.dumps(xmltodict.parse(dossier['_value_1'])))['Response']['fascicolo']['@physdoc']
        except Exception as e:
          print(e)
          id_dossier = "not_found" 
        return id_dossier

    # aggiungi documento in fascicolo identificandolo con i rispettivi phydoc
    def add_document_in_dossier(self, dossier_physdoc, document_physdoc, template=_XML_DOSSIER_IN_DOCUMENT):
       self.client.service.addInFolder(template.format(**{"dossier_physdoc": document_physdoc,"document_physdoc": dossier_physdoc}))

    # cambio dell'utenza per esecuzione delle operazioni
    def set_user(self, user, profile=None):
       self.client.service.setWSUser(user, profile)



