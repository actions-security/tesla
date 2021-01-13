# -*- coding: utf-8 -*-
import glob
import ipaddress
import os
import sys
import threading
import time

import actionslog as log
import ModSecurity
from core import BaseApplication
from tesla.proxy import Proxy
from tesla.server import Server
from tesla.tesla_exception import TeslaException
from tesla.modsec import ModSecurityParser

"""Main module."""


class Tesla(BaseApplication):
    def __init__(self):
        super(Tesla, self).__init__(
            'tesla', description='Tesla Web Application Firewall')

        self.add_argument('dst_host', 'Destination host')
        self.add_argument('dst_port', 'Destination port', type=int)
        self.add_argument('rule_set', 'ModSecurity rule set', nargs='+')
        self.add_argument('--es_host', 'Elasticsearch host')
        self.add_argument('--es_port', 'Elasticsearch port', type=int)
        self.add_argument('--es_user', 'Elasticsearch user')
        self.add_argument('--es_secret', 'Elasticsearch secret')
        self.add_argument('--src-host', 'Source host', default='0.0.0.0')
        self.add_argument('--src-port', 'Source port', type=int, default=9090)

        self._server = None

    @property
    def server(self):
        return self._server

    def setup(self, args=sys.argv[1:]):

        # if (os.environ.get('TESLA_DST_HOST')):
        #     self.args.dst_host = os.environ.get('TESLA_DST_HOST')
        #     self.args.dst_port = os.environ.get('TESLA_DST_PORT')
        #     self.args.rule_set = os.environ.get('TESLA_RULE_SET')
        #     self.args.src_host = os.environ.get('TESLA_SRC_HOST')
        #     self.args.src_port = os.environ.get('TESLA_SRC_PORT')
        # else:
        super(Tesla, self).setup(args)

        try:
            self._src_host = self.args.src_host
            if not self._is_valid_address(self._src_host):
                raise TeslaException(
                    'Address: "%s" is not a valid address!' % self._src_host)

            self._src_port = self.args.src_port
            if not type(self._src_port) == int:
                raise TeslaException('Please inform a valid source port.')

            # dst_host could be a domain
            self._dst_host = self.args.dst_host

            self._dst_port = self.args.dst_port
            if not type(self._dst_port) == int:
                raise TeslaException('Please inform a valid destination port.')

            log.debug('Initializing ModSecurity', component='ModSecurity')

            self._configure_log_handlers()

            self._modsec = ModSecurity.ModSecurity()
            self._modsec.setServerLogCb(self.modsecurity_log_callback)
            self._load_modsec_rules()

            self._server = self._create_server(
                self._src_host,
                self._src_port,
                self._dst_host,
                self._dst_port,
                proxy_creator_func=self._create_proxy)
        except Exception as e:
            log.error(e)
            raise
        
        if not 'pytest' in sys.modules:
            self._modsec_parser = ModSecurityParser(self.args.es_host, self.args.es_port, self.args.es_user, self.args.es_secret)
            thr = threading.Thread(target=self._start_parser)
            thr.start()

    def _configure_log_handlers(self):
        import logging
        instance = log.get_instance()
        modsec_handler = logging.FileHandler(
            instance.get_log_path('modsecurity.log'))

        def modsec_filter(record):
            component = getattr(record, 'component', None)
            print('component:', component, '-' * 80)

            if component == 'ModSecurity':
                return 1
            return 0

        modsec_handler.addFilter(modsec_filter)
        instance.addHandler(modsec_handler)

    def modsecurity_log_callback(self, data, msg):
        log.info(
            'Log from modsecurity',
            component='ModSecurity-Internal',
            modsecurity_msg=msg,
            modsecurity_data=data or 'None')

    def _load_modsec_rules(self):
        self._modsec_rules = ModSecurity.Rules()

        for rule_set in self.args.rule_set:
            for path in glob.iglob(rule_set, recursive=True):
                self._load_modsec_rule_from_filename(path)

        log.debug('Finished loading core rules')

    def _load_modsec_rule_from_filename(self, filename):
        log.debug(
            'Loading core rule set "%s"...' % filename,
            component='ModSecurity')
        if self._modsec_rules.loadFromUri(filename) == 0:
            log.error(
                Exception(self._modsec_rules.getParserError()),
                component='ModSecurity')

    def _create_server(self,
                       src_host,
                       src_port,
                       dst_host,
                       dst_port,
                       proxy_creator_func=None):
        return Server(
            'server',
            src_host,
            src_port,
            dst_host,
            dst_port,
            proxy_creator_func=proxy_creator_func)

    def _is_valid_address(self, address):
        try:
            ipaddress.ip_address(address)
            return True
        except:
            return False

    def _create_proxy(self, dst_host, dst_port):
        transaction = ModSecurity.Transaction(self._modsec, self._modsec_rules)
        if transaction is None:
            log.error(
                Exception('Could not create a new ModSecurity transaction!'),
                component='ModSecurity')
        p = Proxy(dst_host, dst_port, transaction)
        return p
    
    def _start_parser(self):
	    instance = log.get_instance()
	    while True:
		    time.sleep(10)
		    self._modsec_parser.send(instance.get_log_path())
