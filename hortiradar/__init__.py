from .tweety import Tweety


try:
    from .secret import TOKEN, admins, users
except ImportError:
    pass
