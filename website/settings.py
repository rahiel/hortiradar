# Flask settings
DEBUG = False
SQLALCHEMY_DATABASE_URI = "sqlite:///hortiradar.sqlite"
CSRF_ENABLED = True

# Flask-Mail settings
MAIL_USERNAME = "noreply@acba.labs.vu.nl"
MAIL_DEFAULT_SENDER = '"Hortiradar" <noreply@acba.labs.vu.nl>'
MAIL_SERVER = "localhost"
MAIL_PORT = 25
# MAIL_USE_SSL = True

# Flask-User settings
USER_APP_NAME = "Hortiradar"
# Our app is served within the /hortiradar/ subdirectory
USER_CHANGE_PASSWORD_URL      = "/hortiradar/user/change-password"
USER_CHANGE_USERNAME_URL      = "/hortiradar/user/change-username"
USER_CONFIRM_EMAIL_URL        = "/hortiradar/user/confirm-email/<token>"
USER_EMAIL_ACTION_URL         = "/hortiradar/user/email/<id>/<action>"
USER_FORGOT_PASSWORD_URL      = "/hortiradar/user/forgot-password"
USER_INVITE_URL               = "/hortiradar/user/invite"
USER_LOGIN_URL                = "/hortiradar/user/login"
USER_LOGOUT_URL               = "/hortiradar/user/logout"
USER_MANAGE_EMAILS_URL        = "/hortiradar/user/manage-emails"
USER_REGISTER_URL             = "/hortiradar/user/register"
USER_RESEND_CONFIRM_EMAIL_URL = "/hortiradar/user/resend-confirm-email"
USER_RESET_PASSWORD_URL       = "/hortiradar/user/reset-password/<token>"

# Flask-SQLAlchemy
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SECRET_KEY and MAIL_PASSWORD in settings-secret.py
