from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, NoneOf


class RoleForm(FlaskForm):
    username = StringField("username", validators=[DataRequired()])
    role = StringField("role", validators=[DataRequired(), NoneOf(["admin"])])
    action = SelectField("action", choices=[("add", "add"), ("remove", "remove")], validators=[DataRequired()])

class GroupForm(FlaskForm):
    name = StringField("group name", validators=[DataRequired()])
    action = SelectField("action", choices=[("add", "add"), ("remove", "remove")], validators=[DataRequired()])
