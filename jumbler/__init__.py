import logging
import logging.config
import os
import sys
import pprint
import yaml


def __setup_logging(log_config='logging.yml', log_level=logging.INFO):
    root = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(root, 'config', log_config)
    if os.path.exists(path):
        with open(path, 'rt') as cfg_file:
            config = yaml.safe_load(cfg_file.read())
        for _, handler in config['handlers'].items():
            file = handler.get("filename", None)
            if file is None:
                continue
            handler['filename'] = os.path.join(root, 'logs', file)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=log_level)


def main():
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    __setup_logging()
    import server as proxy_server
    proxy_server.start()

if __name__ == "__main__":
    main()
