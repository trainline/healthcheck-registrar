""" Check Formatter """

import copy


class CheckFormatter(object):
    """ Check Formatter """

    def __init__(self):
        self.check = None
        self.info = None

    def format(self, check, info):
        """ Call all the required formatting functions on the check """
        self.check = copy.deepcopy(check)
        self.info = copy.deepcopy(info)
        self._format_http()
        return self.check

    def _format_http(self):
        if 'http' in self.check:
            self.check['http'] = self.check['http'].replace("${PORT}",
                                                            str(self.info['port']))
        else:
            pass
