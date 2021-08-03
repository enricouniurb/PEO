import datetime
import magic
import os

from django import forms
from django.conf import settings
from django.forms.fields import FileField
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from django_form_builder.dynamic_fields import format_field_name
from django_form_builder.forms import BaseDynamicForm
from django_form_builder.dynamic_fields import *
from django import forms

from . import peo_formfields
from . settings import (ETICHETTA_INSERIMENTI_ID,
                        ETICHETTA_INSERIMENTI_LABEL,
                        ETICHETTA_INSERIMENTI_HELP_TEXT)


class PeoDynamicForm(BaseDynamicForm):
    def __init__(self,
                 constructor_dict={},
                 custom_params={},
                 *args,
                 **kwargs):

        self.fields = {}
        self.domanda_bando = custom_params.get('domanda_bando')
        self.descrizione_indicatore = custom_params.get('descrizione_indicatore')
        self.remove_filefields = custom_params.get('remove_filefields')

        # Inserimento manuale del field ETICHETTA
        etichetta_id = format_field_name(ETICHETTA_INSERIMENTI_ID)
        etichetta_data = {'required' : True,
                          'label': ETICHETTA_INSERIMENTI_LABEL,
                          'help_text': ETICHETTA_INSERIMENTI_HELP_TEXT}
        etichetta_field = getattr(peo_formfields,
                                  'CustomCharField')(**etichetta_data)

        if not(custom_params.get('subdescrizioneindicatoreformfield')):
            self.fields[etichetta_id] = etichetta_field
            self.fields[etichetta_id].initial = self.descrizione_indicatore

        super().__init__(fields_source=peo_formfields,
                         initial_fields=self.fields,
                         constructor_dict=constructor_dict,
                         custom_params=custom_params,
                         *args, **kwargs)

        
        if 'sub_descrizione_indicatore_form' in self.data:
            current_value = self.data.get('sub_descrizione_indicatore_form')  
            for key,field in self.fields.items():
                name = getattr(field, 'name') if hasattr(field, 'name') else key    
                if ('submulti_' in name):            
                    if not(name.endswith('submulti_{}'.format(current_value))) and name != 'sub_descrizione_indicatore_form' and name != 'etichetta_inserimento':                    
                        field.disabled = True
                        field.required = False
                    else:                                                             
                        field.disabled = False
         

    def clean(self, *args, **kwargs):
        cleaned_data = super(forms.Form,self).clean()
        for fname in self.fields:
            field = self.fields[fname]
            # se il campo è disabilitato NON va eseguita la validazione
            if field.disabled and not field.required:                
                continue
            # formset is empty or not valid
            if field.is_formset and not field.widget.formset.is_valid():
                errors = field.widget.formset.errors
                self.add_error(fname, errors)
                continue
            # other fields check
            if hasattr(field, 'parent'):
                field = getattr(field, 'parent')
                errors = field.raise_error(fname,
                                            cleaned_data,
                                            **{'domanda_bando': self.domanda_bando,
                                               'allegati': self.remove_filefields})
            else:
                errors = field.raise_error(None,
                                            cleaned_data.get(fname),
                                            **{'domanda_bando': self.domanda_bando,
                                               'allegati': self.remove_filefields})
            if errors:
                self.add_error(fname, errors)
                continue



class MotivazioneForm(forms.Form):
    motivazione = forms.CharField(label= "Motivazione:", widget=forms.Textarea(attrs={"rows":1}))
    punteggio_manuale = PositiveFloatField(label="Punteggio manuale:", required=False)

