from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class ResetPasswordThrottle(AnonRateThrottle):
    scope = "reset_password"


class ChangePasswordThrottle(UserRateThrottle):
    scope = "change_password"


class TransactionThrottle(UserRateThrottle):
    scope = "transaction"


class ShareLinkTransaction(AnonRateThrottle):
    scope = "share_link"
