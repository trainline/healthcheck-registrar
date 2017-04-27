""" Consul Health Check """

import os
import stat
from envmgr_healthchecks.health_checks.health_check import HealthCheck
from envmgr_healthchecks.health_checks.health_check_errors import RegisterError
from envmgr_healthchecks.api.consul.consul_config import ConsulConfig


class ConsulHealthCheck(HealthCheck):
    """ Consul Health Check """

    def __init__(self, **kwargs):
        """
        Keyword Arguments:
            name: the name of the health check registration
            logger: default will be provided if none given
            archive_dir: the health check archive director
            appspec: provide the deployment appspec
            service_slice: blue/green
            service_id:
            api: default will be constructed if you do not provide one
            last_id:
            last_archive_dir:
        """
        HealthCheck.__init__(self, name=kwargs.get('name', ''))
        self.logger = kwargs.get('logger', self.logger)
        self.archive_dir = kwargs.get('archive_dir', None)
        self.appspec = kwargs.get('appspec', None)
        self.service_slice = kwargs.get('service_slice', None)
        self.service_id = kwargs.get('service_id', None)
        self.api = ConsulConfig().get(kwargs.get('api', None))
        self.last_id = kwargs.get('last_id', None)
        self.last_archive_dir = kwargs.get('last_architve_dir', None)

    def register(self):
        """ Register this health check """
        self.logger.info('Registering Consul healthchecks.')
        (healthchecks, scripts_base_dir) = self.find_health_checks(
            'consul',
            self.archive_dir,
            self.appspec
        )
        if healthchecks is None:
            return

        self._validate_checks(healthchecks, scripts_base_dir)
        deployment_slice = self.service_slice
        if deployment_slice is not None and deployment_slice.lower() == 'none':
            deployment_slice = None

        for check_id, check in healthchecks.iteritems():
            service_check_id = self.create_service_check_id(
                self.service_id, check_id)

            if check['type'] == 'script':
                file_path = os.path.join(
                    self.archive_dir, scripts_base_dir, check['script'])

                # Add execution permission to file
                file_stats = os.stat(file_path)
                os.chmod(file_path, file_stats.st_mode | stat.S_IEXEC |
                         stat.S_IXGRP | stat.S_IXOTH)

                # Pass slice name as argument to healthcheck
                if deployment_slice is not None:
                    file_path += ' {0}'.format(deployment_slice)

                self.logger.debug(
                    'Healthcheck {0} full path: {1}'.format(check_id, file_path))
                is_success = self.api.register_script_check(
                    self.service_id,
                    service_check_id,
                    check['name'],
                    file_path,
                    check['interval'])
            elif check['type'] == 'http':
                is_success = self.api.register_http_check(
                    self.service_id,
                    service_check_id,
                    check['name'],
                    check['http'],
                    check['interval'])
            else:
                is_success = False

            if is_success:
                self.logger.info(
                    'Successfuly registered Consul health check \'{0}\''.format(check_id))
            else:
                raise RegisterError(
                    'Failed to register Consul health check \'{0}\''.format(check_id))

    def deregister(self):
        """ deregister this health check """
        if self.last_id is None:
            self.logger.info(
                'Skipping {0} stage as there is no previous deployment.'.format(self.name))
        else:
            self.logger.info(
                'Deregistering Consul healthchecks from previous deployment.')
            previous_appspec = self._get_previous_deployment_appspec(
                self.last_archive_dir)
            if previous_appspec is None:
                self.logger.warning(
                    'Previous deployment directory not found, id: {0}'.format(self.last_id))
            else:
                (healthchecks, _) = self.find_health_checks(
                    'consul', self.last_archive_dir, previous_appspec)
                if healthchecks is None:
                    return
                for check_id, _ in healthchecks.iteritems():
                    service_check_id = self.create_service_check_id(
                        self.service_id, check_id)
                    is_success = self.api.deregister_check(
                        service_check_id)
                    if is_success:
                        self.logger.info(
                            'Successfuly deregistered Consul health check \'{0}\''.format(check_id))
                    else:
                        self.logger.warning(
                            'Failed to deregister Consul health check \'{0}\''.format(check_id))

    def _validate_checks(self, healthchecks, scripts_base_dir):
        ids_list = [identifier.lower() for identifier in healthchecks.keys()]
        if len(ids_list) != len(set(ids_list)):
            raise RegisterError(
                'Consul health checks require unique ids (case insensitive)')

        names_list = [tmp['name'] for tmp in healthchecks.values()]
        if len(names_list) != len(set(names_list)):
            raise RegisterError(
                'Consul health checks require unique names (case insensitive)')

        for check_id, check in healthchecks.iteritems():
            self._validate_check(check_id, check)
            if check['type'] == 'script':
                if check['script'].startswith('/'):
                    check['script'] = check['script'][1:]

                file_path = os.path.join(
                    self.archive_dir, scripts_base_dir, check['script'])
                if not os.path.exists(file_path):
                    raise RegisterError('Couldn\'t find health check script in '
                                        'package with path: {0}'.format(
                                            os.path.join(scripts_base_dir, check['script'])))

    def _validate_check(self, check_id, check):
        if not 'type' in check or (check['type'] != 'script' and check['type'] != 'http'):
            raise RegisterError(
                'Failed to register health check \'{0}\', only \'script\' and \'http\' '
                'check types are supported, found {1} .'.format(
                    check_id, check['type']))
        if check['type'] == 'script':
            required_fields = ['name', 'script', 'interval']
        elif check['type'] == 'http':
            required_fields = ['name', 'http', 'interval']
        for field in required_fields:
            if not field in check:
                raise RegisterError(
                    'Health check \'{0}\' is missing field \'{1}\''.format(check_id, field))
