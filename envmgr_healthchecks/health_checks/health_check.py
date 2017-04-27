""" Health Check """

import os
import yaml
import logging


class HealthCheck(object):
    """ Health Check Base """
    def __init__(self, name=None):
        self.logger = logging.getLogger("HealthCheck")
        self.name = name

    def create_service_check_id(self, service_id, check_id):
        """ create a service id """
        return str(service_id) + ':' + str(check_id)

    def find_health_checks(self, check_type, archive_dir, appspec):
        """ find the health checks """
        relative_path = os.path.join(
            'healthchecks', check_type, 'healthchecks.yml')
        absolute_filepath = os.path.join(archive_dir, relative_path)
        scripts_base_dir = None

        if os.path.exists(absolute_filepath):
            self.logger.debug('Found {0}'.format(relative_path))
            scripts_base_dir = os.path.join('healthchecks', check_type)
            healthchecks_stream = file(absolute_filepath, 'r')
            healthchecks_object = yaml.load(healthchecks_stream)
            if not isinstance(healthchecks_object, dict):
                self.logger.error(
                    '{0} doesn\'t contain valid definition of healthchecks'.format(relative_path))
                healthchecks = None
            else:
                healthchecks = healthchecks_object.get(
                    '{0}_healthchecks'.format(check_type))
        else:
            scripts_base_dir = ''
            self.logger.debug(
                'No {0} found, attempting to find specification in appspec.yml'.format(relative_path))
            healthchecks = appspec.get('{0}_healthchecks'.format(check_type))

        if healthchecks is None:
            self.logger.info('No health checks found.')
        return (healthchecks, scripts_base_dir)

    def _get_previous_deployment_appspec(self, last_archive_dir):
        appspec_filepath = os.path.join(last_archive_dir, 'appspec.yml')
        self.logger.debug(
            'Loading existing deployment appspec file from {0}.' .format(appspec_filepath))
        if os.path.exists(appspec_filepath):
            appspec_stream = file(appspec_filepath, 'r')
            return yaml.load(appspec_stream)
        else:
            return None
