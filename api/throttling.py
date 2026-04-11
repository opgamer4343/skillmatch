from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstUserThrottle(UserRateThrottle):
    scope = "burst"


class SustainedUserThrottle(UserRateThrottle):
    scope = "sustained"


class LoginAnonThrottle(AnonRateThrottle):
    scope = "login_anon"


class LoginUserThrottle(UserRateThrottle):
    scope = "login_user"
