import base64
import json
import logging

import requests

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError
from .requests import HTTPBasicAuthKey

_logger = logging.getLogger(__name__)


class VendusMixin(models.AbstractModel):
    _name = 'vendus.mixin'
    _description = 'Vendus Mixin'

    vendus_id = fields.Char('Vendus ID', company_dependent=False, copy=False)

    # -------------------------------------------------------------------------
    # METHODS TO BE IMPLEMENTED
    # -------------------------------------------------------------------------

    @api.model
    def _get_endpoint_url(self):
        """
        Returns the relative endpoint of the model. Eg: 'products/'
        :return: string with the model relative endpoint
        """
        return NotImplementedError('Method _get_endpoint_url not implemented for %s' % self._name)

    def prepare_create_vendus_record(self):
        """
        Prepares a dict to create a vendus record through the Vendus API.
        :return: dict with values
        """
        return NotImplementedError('Method prepare_create_vendus_record not implemented for %s' % self._name)

    def prepare_update_vendus_record(self):
        """
        Prepares a dict to update a vendus record through the Vendus API.
        :return: dict with values
        """
        return NotImplementedError('Method prepare_update_vendus_record not implemented for %s' % self._name)

    def prepare_import_from_vendus(self, response):
        """
        Prepares a dict to create a record with info from vendus.
        :return: dict with values
        """
        return NotImplementedError('Method prepare_import_from_vendus not implemented for %s' % self._name)

    def prepare_update_from_vendus(self, vendus_record_dict):
        """
        Prepares a dict to update a record with info from vendus.
        :return: dict with values
        """
        return NotImplementedError('Method prepare_update_from_vendus not implemented for %s' % self._name)

    def prepare_read_params(self):
        """
        Prepares a dict to use as params for get requests.
        :return: dict with values
        """
        return NotImplementedError('Method prepare_read_params not implemented for %s' % self._name)

    # -------------------------------------------------------------------------
    # REQUEST METHODS
    # -------------------------------------------------------------------------

    @api.model
    def vendus_request(self, method, endpoint, **kwargs):
        """
        Encapsulation of the vendus API call and exception handling.
        :param method: API call type (eg: 'get' or 'post')
        :param endpoint: API endpoint without base url (eg: 'products/')
        :param kwargs: optional arguments to be passed such as a data dict with values.
        Should match the available kwargs for the request method of the requests library.
        :return: A list with records or a dict with only one record (when doing an action on a single record).
        :rtype: list or dict
        """
        api_key = False
        if self.env.user.id == SUPERUSER_ID or self._context.get('SUPERUSER_ID', True):
            api_key = self.env.company.vendus_api_key
        elif user := self.env['vendus.user'].search([('vendus_id', '=', self.env.user.vendus_id.vendus_id)]):
            api_key = user.api_key

        if not api_key:
            raise ValidationError(_('Vendus API Key not found for this company.'))
        if endpoint and endpoint[:1] != '/':
            endpoint += '/'
        try:
            if 'data' in kwargs:
                kwargs['json'] = kwargs.pop('data')
            if 'json' in kwargs:
                # Remove empty values from data dict
                kwargs['json'] = {k: v for k, v in kwargs['json'].items() if v}
            response = requests.request(
                method,
                'https://www.vendus.pt/ws/v1.2/' + str(endpoint),
                **dict(auth=HTTPBasicAuthKey(api_key), **kwargs)
            )
        except AttributeError as e:
            raise ValidationError(e)
        except Exception as e:
            _logger.warning("URL Call Error. URL: %s" % (e.__str__()))
            raise ValidationError(e)
        else:
            try:
                content = json.loads(response.content.decode('utf-8'))
            except:
                content = base64.b64encode(response.content)
            if not response.ok:
                if response.status_code == 404 and content['errors'][0]['code'] == 'A001':
                    return []  # Vendus returns a 404 when there's no record in a specific endpoint
                error_msgs = '%s ' % ', '.join([e['message'] for e in content['errors']])
                _logger.error(error_msgs)
                raise ValidationError(error_msgs)
            else:
                return content

    def vendus_create(self):
        """
        Creates the record in the vendus environment and updates vendus_id field.
        :return: Response dict
        """
        self.ensure_one()
        response = self.vendus_request('post', self._get_endpoint_url(), json=self.prepare_create_vendus_record())
        _logger.info(f'Vendus: {self._description} created with the id {response["id"]}')
        self.vendus_id = str(response['id'])
        return response

    def vendus_update(self):
        """
        Updates the record in the vendus environment.
        :return: True if operation was successful
        """
        self.ensure_one()
        endpoint = self._get_endpoint_url() + str(self.vendus_id)
        response = self.vendus_request('patch', endpoint, json=self.prepare_update_vendus_record())
        _logger.info(f'Vendus: {self._description} updated with the id {response["id"]}')
        return True

    def vendus_delete(self):
        """
        Deletes a record from the vendus environment.
        :return: Deleted id
        """
        self.ensure_one()
        if self.vendus_id:
            response = self.vendus_request('delete', self._get_endpoint_url() + str(self.vendus_id))
            _logger.info(response)
            if str(response['id']) == self.vendus_id and response['status'] == 'deleted':
                _logger.info(f'Vendus: {self._description} deleted with the id {response["id"]}')
                self.vendus_id = False
            return str(response['id'])

    def vendus_search(self, **kwargs):
        return NotImplementedError('Method vendus_search not implemented for %s' % self._name)

    def vendus_read(self):
        self.ensure_one()
        endpoint = self._get_endpoint_url() + str(self.vendus_id)
        response = self.vendus_request('get', endpoint, params=self.prepare_read_params())
        return response

    @api.model
    def vendus_list(self):
        response = self.with_context(SUPERUSER_ID=self._context.get('SUPERUSER_ID', True)).vendus_request('get', self._get_endpoint_url())
        # for record in response:
        #     print(record)
        return response

    # -------------------------------------------------------------------------
    # IMPORT METHODS
    # -------------------------------------------------------------------------

    @api.model
    def import_single_record_from_vendus(self, vendus_id):
        response = self.vendus_request('get', self._get_endpoint_url() + str(vendus_id))
        if response:
            return self.create([self.prepare_import_from_vendus(response)])

    @api.model
    def import_all_records_from_vendus(self, override=False):
        """
        Imports all records and returns created and updated stats.
        :param override: If override is True and if there's a already a matching record in Odoo, that record will be
        updated with the vendus data from the API.
        :return:
        """
        response = self.with_context(SUPERUSER_ID=self._context.get('SUPERUSER_ID', True)).vendus_list()
        vals_list = []
        updated = 0
        for vendus_dict in response:
            # Search
            rec = self.find_record_by_domain_list(vendus_dict)
            if rec and override:
                rec.write(rec.prepare_update_from_vendus(vendus_dict))
                rec.flush()
                updated += 1
            elif not rec:
                vals_list.append(self.prepare_import_from_vendus(vendus_dict))
        # Create
        if vals_list:
            self.create(vals_list)
        _logger.info(f"Vendus Import: {len(vals_list)} {self._description} created!")
        _logger.info(f"Vendus Import: {updated} {self._description} updated!")
        return len(vals_list), updated

    # -------------------------------------------------------------------------
    # BASE FIND METHODS
    # -------------------------------------------------------------------------

    @api.model
    def find_record_by_domain_list(self, record):
        """
        Tries to find a record from a list of fields. The first record found is returned
        :param record: vendus record dict
        :return: recordset
        """
        domain_list = self.prepare_find_record_by_domain_list(record)
        for domain in domain_list:
            if domain[2]:
                res = self.search([domain], limit=1)
                if res:
                    return res
        return self

    def prepare_find_record_by_domain_list(self, record):
        """
        This may need to be implemented by each class to add a list of domains to be used in the record search to match
        with the vendus records.
        :param record: vendus record dict
        :return: list of tuples
        """
        return [('vendus_id', '=', record['id'])]
