import logging
import logging.config
import os
import sys
import pprint
import yaml


def __setup_logging(log_cfg_file='logging.yml', log_level=logging.INFO):
    root = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(root, 'conf', log_cfg_file)
    if os.path.exists(path):
        with open(path, 'rt') as cfg_file:
            log_cfg = yaml.safe_load(cfg_file.read())
        for _, handler in log_cfg['handlers'].items():
            file = handler.get("filename", None)
            if file is None:
                continue
            handler['filename'] = os.path.join(root, 'logs', file)
        logging.config.dictConfig(log_cfg)
        return log_cfg
    else:
        logging.basicConfig(level=log_level)
        return {}


def main():
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from server import SanicServer
    server = SanicServer({'host': '0.0.0.0', 'port': 5000, 'debug': True}, __setup_logging())
    server.start()

if __name__ == "__main__":
    main()
