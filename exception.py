
class AppException(Exception):
    pass


# Implemented
class InvalidBucketName(AppException):
    status_code = 400
    message = 'xxx'


class MetadataTooLarge(AppException):
    status_code = 400
    message = 'xxx'


class InvalidArgument(AppException):
    status_code = 400
    message = 'xxx'


class TooManyBuckets(AppException):
    status_code = 400
    message = 'xxx'


class InvalidDigest(AppException):
    status_code = 400
    message = 'xxx'


class EntityTooLarge(AppException):
    status_code = 400
    message = 'xxx'


class AccessDenied(AppException):
    status_code = 403
    message = 'xxx'


class SignatureDoesNotMatch(AppException):
    status_code = 403
    message = 'xxx'


class InvalidAccessKeyId(AppException):
    status_code = 403
    message = 'xxx'


class NoSuchBucket(AppException):
    status_code = 404
    message = 'xxx'


class NoSuchKey(AppException):
    status_code = 404
    message = 'xxx'


class NotSuchBucketPolicy(AppException):
    status_code = 404
    message = 'xxx'


class MethodNotAllowed(AppException):
    status_code = 405
    message = 'xxx'


class BucketAlreadyExists(AppException):
    status_code = 409
    message = 'xxx'


class BucketNotEmpty(AppException):
    status_code = 409
    message = 'xxx'


class MissingContentLength(AppException):
    status_code = 411
    message = 'xxx'


class InternalError(AppException):
    status_code = 500
    message = 'xxx'


class NotImplemented(AppException):
    status_code = 501
    message = 'xxx'
