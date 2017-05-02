""" Sensu Health Check """

import os
import stat
import json
import sys
import re
from jsonschema import Draft4Validator
from envmgr_healthchecks.health_checks.health_check import HealthCheck
from envmgr_healthchecks.health_checks.health_check_errors import RegisterError


class SensuHealthCheck(HealthCheck):
    """ Sensu Health Check """

    def __init__(self, name=None, **kwargs):
        HealthCheck.__init__(self, name=name)
        self.platform = kwargs.get('platform', None)
        self.instance_tags = kwargs.get('instance_tags', None)
        self.sensu = kwargs.get('sensu', None)
        self.service_id = kwargs.get('service_id', None)
        self.service_slice = kwargs.get('service_slice', None)
        self.last_id = kwargs.get('last_id', None)
        self.last_archive_dir = kwargs.get('last_archive_dir', None)
        self.archive_dir = kwargs.get('archive_dir', None)
        self.appspec = kwargs.get('appspec', None)
        self.check_id = kwargs.get('check_id', None)
        self.check = kwargs.get('check', None)
        self.logger = kwargs.get('logger', self.logger)
        self.schema = self._get_schema()

    def deregister(self):
        """ deregister this health check """
        if self.last_id is None:
            self.logger.info(
                'Skipping {0} stage as there is no previous deployment.'.format(self.name))
        else:
            self.logger.info(
                'Deregistering Sensu healthchecks from previous deployment.')
            previous_appspec = self._get_previous_deployment_appspec(
                self.last_archive_dir)
            if previous_appspec is None:
                self.logger.warning(
                    'Previous deployment directory not found, id: {0}'.format(self.last_id))
            else:
                (healthchecks, _) = self.find_health_checks(
                    'sensu', self.last_archive_dir, previous_appspec)
                if healthchecks is None:
                    return
                for check_id, _ in healthchecks.iteritems():
                    check_definition_absolute_path = os.path.join(
                        self.sensu['sensu_check_path'],
                        self._create_sensu_definition_filename(self.service_id, check_id))
                    if os.path.exists(check_definition_absolute_path):
                        os.remove(check_definition_absolute_path)

    def register(self):
        """ Register this health check """
        self.logger.info('Registering Sensu checks.')
        (sensu_checks, scripts_base_dir) = self.find_health_checks(
            'sensu', self.archive_dir, self.appspec)
        if sensu_checks is None:
            self.logger.info('No Sensu checks to register.')
            return
        self._validate_checks(
            sensu_checks, scripts_base_dir)
        for check_id, check in sensu_checks.iteritems():
            self._register_check(
                self.check_id, self.check)

    def _create_sensu_definition_filename(self, service_id, check_id):
        return '{0}-{1}.json'.format(service_id, check_id)

    def _register_check(self, check_id, check):
        if 'local_script' in check:
            script_absolute_path = check['local_script']
            self.logger.info(
                'Setting mode on file: {0}'.format(script_absolute_path))
            file_stat = os.stat(script_absolute_path)
            os.chmod(
                script_absolute_path,
                file_stat.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        elif 'server_script' in check:
            script_absolute_path = check['server_script']
        else:
            raise RegisterError('Missing script property \'local_script\' nor '
                                '\'server_script\' in check definition')

        self.logger.debug('Sensu check {0} script path: {1}'.format(
            check_id, script_absolute_path))

        check_definition = self._generate_check_definition(
            check, script_absolute_path)
        check_definition_filename = self._create_sensu_definition_filename(
            self.service_id, check_id)
        check_definition_absolute_path = os.path.join(
            self.sensu['sensu_check_path'], check_definition_filename)
        is_success = self._write_check_definition_file(
            check_definition, check_definition_absolute_path)
        if not is_success:
            raise RegisterError(
                'Failed to register Sensu check \'{0}\''.format(check_id))

    def _write_check_definition_file(self, check_definition, check_definition_absolute_path):
        try:
            with open(check_definition_absolute_path, 'w') as check_definition_file:
                check_definition_file.write(json.dumps(
                    check_definition, sort_keys=True, indent=4, separators=(',', ': ')))
            self.logger.info('Created Sensu check definition: {0}'.format(
                check_definition_absolute_path))
            return True
        except Exception:
            self.logger.exception(sys.exc_info()[1])
            return False

    def _validate_checks(self, checks, scripts_base_dir):
        for check_id, check in checks.iteritems():
            self._validate_check_properties(
                check_id, check)
            self._validate_check_script(
                check, scripts_base_dir)
        self._validate_unique_ids(checks)
        self._validate_unique_names(checks)

    def _validate_check_properties(self, check_id, check):
        Draft4Validator(self.schema).validate(check)
        if not re.match(r'^[\w\.-]+$', check['name']):
            raise RegisterError('Health check name \'{0}\' doesn\'t match required '
                                'Sensu name expression {1}'.format(check['name'], r'/^[\w\.-]+$/'))
        if 'local_script' in check and 'server_script' in check:
            raise RegisterError(
                'Failed to register health check \'{0}\', you can use either '
                '\'local_script\' or \'server_script\', but not both.'.format(check_id))
        if not ('local_script' in check or 'server_script' in check):
            raise RegisterError(
                'Failed to register health check \'{0}\', you need at least one of: '
                '\'local_script\' or \'server_script\''.format(check_id))
        if 'standalone' in check and 'aggregate' in check:
            if check['standalone'] is True and check['aggregate'] is True:
                raise RegisterError(
                    'Either standalone or aggregate can be True at the same time')
            if check['standalone'] is False and check['aggregate'] is False:
                raise RegisterError(
                    'Either standalone or aggregate can be False at the same time')

    def _validate_check_script(self, check, local_scripts_base_dir):
        if 'local_script' in check:
            if check['local_script'].startswith('/'):
                check['local_script'] = check['local_script'][1:]
            absolute_file_path = os.path.join(
                self.archive_dir, local_scripts_base_dir, check['local_script'])
            if not os.path.exists(absolute_file_path):
                raise RegisterError(
                    'Couldn\'t find Sensu check script in package with path: {0}'.format(
                        os.path.join(local_scripts_base_dir, check['local_script'])))
            check['local_script'] = absolute_file_path
        elif 'server_script' in check:
            absolute_file_path = self._find_sensu_plugin(
                self.sensu['healthcheck_search_paths'], check['server_script'])
            if absolute_file_path is None:
                raise RegisterError(
                    'Couldn\'t find Sensu plugin script: {0}\nPaths searched: {1}'.format(
                        check['server_script'], self.sensu['healthcheck_search_paths']))
            check['server_script'] = absolute_file_path

    def _find_sensu_plugin(self, plugin_paths, script_filename):
        for plugin_path in plugin_paths:
            script_filepath = os.path.join(plugin_path, script_filename)
            if os.path.exists(script_filepath):
                return script_filepath
        return None

    def _validate_unique_ids(self, checks):
        check_ids = [check_id.lower() for check_id in checks.keys()]
        if len(check_ids) != len(set(check_ids)):
            raise RegisterError(
                'Sensu check definitions require unique ids (case insensitive)')

    def _validate_unique_names(self, checks):
        check_names = [check['name'] for check in checks.values()]
        if len(check_names) != len(set(check_names)):
            raise RegisterError(
                'Sensu check definitions require unique names (case insensitive)')

    def _generate_check_definition(self, check, script_absolute_path):
        platform = self.platform
        instance_tags = self.instance_tags
        logger = self.logger
        deployment_slice = self.service_slice
        if deployment_slice is not None and deployment_slice.lower() == 'none':
            deployment_slice = None

        def _get_command():
            if platform == 'windows':
                command = '{0} "{1}"'.format(
                    'powershell.exe -NonInteractive -NoProfile -ExecutionPolicy '
                    'Bypass -file', script_absolute_path)
            else:
                command = script_absolute_path

            script_args = check.get('script_arguments', '')

            # Append slice value for local scripts
            if 'local_script' in check:
                script_args = ' '.join(
                    filter(None, (script_args, deployment_slice)))

            return '{0} {1}'.format(command, script_args).rstrip()

        def _get_override_chat_channel():
            override_chat_channel = check.get('override_chat_channel', None)
            if override_chat_channel is not None:
                return ','.join(override_chat_channel)
            return 'undef'

        def _get_override_notification_email(check):
            override_notification_email = check.get(
                'override_notification_email', None)
            if override_notification_email is None:
                if check.get('notification_email') is not None:
                    logger.warning(
                        '\'notification_email\' property is deprecated, please use '
                        '\'override_notification_email\' instead')
                    override_notification_email = check.get(
                        'notification_email', None)
            if override_notification_email is not None:
                return ','.join(override_notification_email)
            return 'undef'

        def _get_override_notification_settings():
            override_notification_settings = check.get(
                'override_notification_settings', None)
            if override_notification_settings is None:
                if check.get('team', None) is not None:
                    logger.warning(
                        '\'team\' property is deprecated, please use \'override_'
                        'notification_settings\' instead')
                    override_notification_settings = check.get('team', None)
            return override_notification_settings

        check_definition = {
            'checks': {
                check['name']: {
                    'aggregate': check.get('aggregate', False),
                    'alert_after': check.get('alert_after', 600),
                    'command': _get_command(),
                    'handlers': ['default'],
                    'interval': check.get('interval'),
                    'notification_email': _get_override_notification_email(check),
                    'occurrences': check.get('occurrences', 5),
                    'page': check.get('paging_enabled', False),
                    'project': check.get('project', False),
                    'realert_every': check.get('realert_every', 30),
                    'runbook': check.get('runbook', 'Please provide useful '
                                         'information to resolve alert'),
                    'sla': check.get('sla', 'No SLA defined'),
                    'slack_channel': _get_override_chat_channel(),
                    'standalone': check.get('standalone', True),
                    'subscribers': ['sensu-base'],
                    'tags': [],
                    'team': _get_override_notification_settings(),
                    'ticket': check.get('ticketing_enabled', False),
                    'timeout': check.get('timeout', 120),
                    'tip': check.get('tip', 'Fill me up with information')
                }
            }
        }

        custom_instance_tags = {
            k: v for k, v in instance_tags.iteritems() if not k.startswith('aws:')}
        for key, value in custom_instance_tags.iteritems():
            name = check['name']
            check_definition['checks'][name]['ttl_' + key.lower()] = value

        return check_definition

    def _get_schema(self):
        return {
            "$schema": "http://json-schema.org/schema#",

            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "interval": {"type": "number"},
                "realert_every": {"type": "number"},
                "timeout": {"type": "number"},
                "occurrences": {"type": "number"},
                "refresh": {"type": "number"},
                "tip": {"type": ["string", "boolean"]},
                "runbook": {"type": ["string", "boolean"]},
                "standalone": {"type": "boolean"},
                "aggregate": {"type": "boolean"},
                "ticketing_enabled": {"type": "boolean"},
                "paging_enabled": {"type": "boolean"},
                "project": {"type": "boolean"},
                "team": {"type": "string"},
                "override_notification_settings": {"type": "string"},
                "notification_email": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                    }
                },
                "override_notification_email": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                    }
                },
                "override_chat_channel": {
                    "type": "array",
                    "items": {"type": "string"}
                },

                "page": {"type": "boolean"}
            },
            "required": ["name", "interval"]
        }
