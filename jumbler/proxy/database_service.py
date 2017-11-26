import logging
_LOG = logging.getLogger(__name__)


class DatabaseService(object):
    '''
    Database service interacts with Database layer to store Selenium Grid Hub/Node information
    '''

    def __init__(self, loop):
        self.loop = loop

    def find_selenium_node(self, browser, os_system):
        return '', ''

    async def update_node_state(self, node_id, state):
        pass

    async def persist_node(self, node_info, prev_state):
        pass
