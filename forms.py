from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SubmitField, PasswordField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = EmailField('Mail ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('LOG IN')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    email = EmailField('Mail ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('SIGN UP')

