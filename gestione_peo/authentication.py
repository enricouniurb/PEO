from djangosaml2.backends import Saml2Backend
from sqlalchemy import true


class ModifiedSaml2Backend(Saml2Backend):

    # def _update_user(self, user, attributes: dict, attribute_mapping: dict, force_save: bool = False):
    #     if 'eduPersonEntitlement' in attributes:
    #         if 'some-entitlement' in attributes['eduPersonEntitlement']:
    #             user.is_staff = True
    #             force_save = True
    #         else:
    #             user.is_staff = False
    #             force_save = True
    #     return super()._update_user(user, attributes, attribute_mapping, force_save)

    def is_authorized(self, attributes: dict, attribute_mapping: dict, idp_entityid: str, assertion_info: dict, **kwargs):        
        """ Hook to allow custom authorization policies based on SAML attributes. True by default. """
        if 'eduPersonPrincipalName' in attributes:
            eduPersonPrincipalName = attributes['eduPersonPrincipalName'][0] if isinstance(attributes['eduPersonPrincipalName'], list) else attributes['eduPersonPrincipalName']
            if eduPersonPrincipalName.endswith('_staff@uniurb.it'):
                return True
            else:
                return False
        return False