import argparse
import logging
import logging.config
import os
import sys
import pprint
import yaml
from pkg_resources import get_distribution


def __setup_logging(log_cfg_file='logging.yml', log_level=logging.INFO):
    root = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(root, 'conf', log_cfg_file)
    if os.path.exists(path):
        with open(path, 'rt') as cfg_file:
            log_cfg = yaml.safe_load(cfg_file.read())
        for _, handler in log_cfg['handlers'].items():
            file = handler.get('filename', None)
            if file is None:
                continue
            handler['filename'] = os.path.join(root, 'logs', file)
        logging.config.dictConfig(log_cfg)
        return log_cfg
    else:
        logging.basicConfig(level=log_level)
        return {}


def main(*arguments):
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    # print(get_distribution(__name__).get_metadata('PKG-INFO'))
    # from email import message_from_string
    # pkg_info = (arguments and arguments[0]) or message_from_string(get_distribution(__name__).get_metadata('PKG-INFO'))
    # parser = argparse.ArgumentParser(usage=pkg_info['Description'])
    # parser.add_argument('-v', '--version', action='version', version=pkg_info['Version'])
    parser = argparse.ArgumentParser(usage='Jumbler', allow_abbrev=False)
    parser.add_argument('-v', '--version', action='version', version='1.0.0.dev1')
    parser.add_argument('-H', '--host', action='store', default='0.0.0.0', required=False, help='Proxy Host Address. Default: \'0.0.0.0\'')
    parser.add_argument('-p', '--port', action='store', default=5000, type=int, required=False, help='Proxy Host Port. Default: 5000')
    parser.add_argument('-m', '--mode', action='store', default='hypersh', required=False, choices=['docker', 'hypersh'], help='Provider mode')
    parser.add_argument('-ep', '--endpoint', action='store', default='', required=False,
                        help='Provider REST Endpoint. It\'s required in Docker Provider mode')
    parser.add_argument('--debug', action='store', default=False, nargs='?', const=True, type=bool, help='Debug mode')
    args = parser.parse_args()

    server_cfg = {'host': args.host, 'port': args.port, 'debug': args.debug}
    business_cfg = {'mode': args.mode, 'endpoint': args.endpoint}
    print(server_cfg)
    print(business_cfg)
    from server import SanicServer
    server = SanicServer(server_cfg, business_cfg, __setup_logging())
    server.start()

if __name__ == '__main__':
    main({'version': 'dev', 'description': ''})
