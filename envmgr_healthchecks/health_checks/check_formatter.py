""" Check Formatter """


class CheckFormatter(object):
    """ Check Formatter """
    def __init__(self):
        self.check = None

    def format(self, check, info):
        """ Call all the required formatting functions on the check """
        self.check = check
        self._format_http(check, info)
        return check

    def _format_http(self, check=None, info=None):
        if 'http' in check:
            self.check['http'] = check['http'].replace("${PORT}", info['port'])
        else:
            pass
