class UserAwareDummyRequest:
    def __init__(self, original_request):
        self._original_request = original_request
        self._user = None

    def __getattr__(self, name):
        return getattr(self._original_request, name)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
