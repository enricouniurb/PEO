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

        # Inserimento manuale del field ETICHETTA
        etichetta_id = format_field_name(ETICHETTA_INSERIMENTI_ID)
        etichetta_data = {'required' : True,
                          'label': ETICHETTA_INSERIMENTI_LABEL,
                          'help_text': ETICHETTA_INSERIMENTI_HELP_TEXT}
        etichetta_field = getattr(peo_formfields,
                                  'CustomCharField')(**etichetta_data)
        self.fields[etichetta_id] = etichetta_field
        self.fields[etichetta_id].initial = self.descrizione_indicatore

        super().__init__(fields_source=peo_formfields,
                         initial_fields=self.fields,
                         constructor_dict=constructor_dict,
                         custom_params=custom_params,
                         *args, **kwargs)

        
        if 'sub_descrizione_indicatore_form' in self.data:
            current_value = self.data.get('sub_descrizione_indicatore_form')
            
            # if 'etichetta_inserimento' in self.data and 'etichetta_inserimento_submulti_{}'.format(current_value) in self.data:
            #     if self.data['etichetta_inserimento_submulti_{}'.format(current_value)] not in self.data['etichetta_inserimento']:
            #         self.data['etichetta_inserimento'] += ' ' + self.data['etichetta_inserimento_submulti_{}'.format(current_value)]

            for key,field in self.fields.items():
                name = getattr(field, 'name') if hasattr(field, 'name') else key                
                if name.find('submulti_') and not(name.endswith('submulti_{}'.format(current_value))) and name != 'sub_descrizione_indicatore_form' and name != 'etichetta_inserimento':
                    field.disabled = True
                    field.required = False
                else:                                                             
                    field.disabled = False

        # Corretto per la classe base BaseDynamicForm
        # if constructor_dict:
        #     for key, value in constructor_dict.items():                        
        #         if (hasattr(custom_field, 'name') and custom_field.name == 'sub_descrizione_indicatore_form'):
        #             if 'sub_descrizione_indicatore_form' in self.data:
        #                 current_value = self.data.get('sub_descrizione_indicatore_form')
        #                 for field in fields:
        #                     name = getattr(field, 'name') if hasattr(field, 'name') else field_id
        #                     if not(name.endswith('submulti_{}'.format(current_value))) and name != 'sub_descrizione_indicatore_form':
        #                         field.disabled = True
        #                         field.required = False
        #                     else: 
        #                         field.disabled = False
         

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
                                            **kwargs)
            else:
                errors = field.raise_error(None,
                                            cleaned_data.get(fname),
                                            **kwargs)
            if errors:
                self.add_error(fname, errors)
                continue