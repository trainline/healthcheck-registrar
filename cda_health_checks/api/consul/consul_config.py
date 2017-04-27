""" Consul API Configuration Details """


class ConsulConfig(object):
    """ Consul Configuration """

    def __init__(self):
        pass

    def get(self, config=None):
        """ Get the confiugration for Consul API """
        if config is not None:
            return config
        default_config = {
            'aws': {'access_key_id': None, 'aws_secret_access_key': None,
                    'deployment_logs': {'bucket_name': None, 'key_prefix': None}},
            'consul': {'host': 'localhost', 'port': 8500, 'scheme': 'http',
                       'acl_token': None, 'version': 'v1'},
            'sensu': {
                'healthcheck_search_paths': ['/etc/some_fake_path', '/opt/sensu_server_scripts'],
                'sensu_check_path': '/etc/sensu/conf.d/checks.local'
            },
            'logging': {
                'version': 1,
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'stream': 'ext://sys.stdout'
                    }
                },
                'root': {
                    'level': 'DEBUG',
                    'handlers': ['console']
                }
            },
            'startup': {
                'delay_in_ms_between_readiness_check': 5000,
                'max_wait_for_instance_readiness_in_ms': 1800000,
                'semaphore_filepath': None,
                'wait_for_instance_readiness': False
            }
        }
        return default_config
