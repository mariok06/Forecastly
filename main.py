from flask import Flask, render_template, url_for, redirect, flash, abort
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from forms import RegisterForm, LoginForm
from functools import wraps
from forecast import Forecast
import logging
import bcrypt
import os

# Creates an instance of Flask
weather_app = Flask(__name__)
weather_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Connects Bootstrap5 with the app
Bootstrap5(weather_app)

# Creates a database
weather_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy()
db.init_app(weather_app)

# Manages User Log Ins and Outs
login_manager = LoginManager()
login_manager.init_app(weather_app)
login_manager.login_view = 'register'
login_manager.login_message = 'Please sign up to access this page.'

# Error Logger
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d %B %Y %H:%M:%S')


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(100))
    city = db.Column(db.String(100))
    email = db.Column(db.String(100))
    password = db.Column(db.String(200))

with weather_app.app_context():
    db.create_all()

forecast = Forecast()

@weather_app.route('/')
def home():
    return render_template('home.html', current_user=current_user)


@weather_app.route('/forecast', methods=['GET', 'POST'])
@login_required
def weather_forecast():
    try:
        logging.info(f'User authenticated: {current_user.is_authenticated}')
        logging.info(f'User city: {current_user.city}')
        current_user_city = current_user.city

        weather_dict = forecast.curr_weather_data(current_user_city)
        forecast_data, avg_temp_df, avg_preci_df, hourly_forecast_data = forecast.get_forecast(current_user_city)

        linechartJSON, piechartJSON, scatterchartJSON = forecast.create_charts(forecast_data, avg_temp_df, avg_preci_df)

        return render_template('forecast.html', weather_data=weather_dict,
                           forecast=hourly_forecast_data, linechartJSON=linechartJSON, piechartJSON=piechartJSON,
                           scatterchartJSON=scatterchartJSON, usercity=current_user_city, current_user=current_user)

    except Exception as e:
        logging.error(f'Error fetching weather forecast: {e}')
        return redirect(url_for('home'))


@weather_app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password = bytes(form.password.data.encode('utf-8'))
        salt = bytes(bcrypt.gensalt())
        hashed_upw = bcrypt.hashpw(password=password, salt=salt)

        new_user = User(
            name = form.name.data.lower(),
            city = form.city.data.lower(),
            email = form.email.data.lower(),
            password= hashed_upw,
        )

        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()

        if not user:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('forecast'))
        else:
            flash('User already exists! Please Log In.')
        return redirect(url_for('login'))

    return render_template('register.html', form=form, current_user=current_user)


@weather_app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()

        if user:
            user_pw = bcrypt.checkpw(password=bytes(form.password.data.encode('utf-8')), hashed_password=bytes(user.password))
            if user_pw:
                login_user(user)
                return redirect(url_for('weather_forecast'))
            else:
                flash("Incorrect password. Please try again!")
                return redirect(url_for('login'))
        else:
            flash("User doesn't exist. Kindly register with us!")
            return redirect(url_for('register'))

    return render_template('login.html', form=form, current_user=current_user)

@weather_app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    weather_app.run(debug=True, port=5007)

