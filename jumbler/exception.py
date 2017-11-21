import logging

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    ''' Base error with common task'''

    def __init__(self, message='', ex=None, level=logging.DEBUG):
        self.message = message
        if ex:
            logger.log(level, message, exc_info=True)
        else:
            logger.log(level, message)


class ValidationError(BusinessError):
    ''' Validation error '''

    def __init__(self, message='', ex=None, level=logging.DEBUG):
        super(ValidationError, self).__init__(message, ex, level)


class DatabaseError(BusinessError):
    ''' Database error in business aspect '''

    def __init__(self, message='', ex=None):
        super(DatabaseError, self).__init__(message, ex, logging.DEBUG)


class ExistingError(BusinessError):
    ''' Existing error with message and existed object '''

    def __init__(self, message, existence):
        super(ExistingError, self).__init__(message, None, logging.DEBUG)
        self.message = message
        self.existence = existence


class RequestError(BusinessError):
    ''' Request error from REST-API of 3rd party '''

    def __init__(self, message='', ex=None, level=logging.DEBUG):
        super(RequestError, self).__init__(message, ex, level)


class ExecutionError(BusinessError):
    ''' Execution error for controller '''

    def __init__(self, message='', ex=None, level=logging.DEBUG):
        super(ExecutionError, self).__init__(message, ex, level)


class NotFoundError(BusinessError):
    ''' Error when not finding anything '''

    def __init__(self, message='', ex=None, where=None, level=logging.DEBUG):
        super(NotFoundError, self).__init__(message, ex, level)
        self.where = where


class LimitedError(BusinessError):
    ''' Error when exceed any limit '''

    def __init__(self, message='', ex=None, currentCount=0, level=logging.DEBUG):
        super(LimitedError, self).__init__(message, ex, level)
        self.currentCount = currentCount
