from flask import Flask, render_template, redirect, request, url_for, flash,g,abort,Response
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_bcrypt import Bcrypt
from datetime import date,timedelta,datetime
import time
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import find_dotenv,load_dotenv



dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

app = Flask(__name__) 
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)  # Adjust duration as needed
app.config["SESSION_COOKIE_SECURE"] = True  # Use HTTPS in production
app.config["REMEMBER_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"  # Prevent cross-site request forgery
db = SQLAlchemy()
login_manager = LoginManager()
flask_bcrypt = Bcrypt()


db.init_app(app)
login_manager.init_app(app)
flask_bcrypt.init_app(app)


class Users(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key = True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000),unique=True)
    tasks = db.relationship("Tasks", back_populates = "user")
    def __repr__(self):
        return '<User %r>' % self.name
    

class Tasks(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer,primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    task = db.Column(db.String(250),nullable = False)
    user = db.relationship("Users", back_populates = "tasks")
    date = db.Column(db.String(200))
    start = db.Column(db.String(200))
    end = db.Column(db.String(200))
    completed = db.Column(db.Boolean, default=False)
    details = db.Column(db.Text)
    everyday = db.Column(db.Boolean, default=False)
    all_day = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Tasks %r>' % self.task


with app.app_context():
    db.create_all()


def convert_time_format(iso_time):
    dt_object = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M")
    return dt_object.strftime("%B %d, %Y | %H:%M")

@login_manager.user_loader
def load_user(user_id):
    return  db.session.get(Users, int(user_id))


@app.route("/",methods = ["GET","POST"])
def home():
    return render_template("index.html")

@app.route("/register",methods=["GET","POST"])
def register():
    if Users.query.filter_by(name=request.form.get("name")).first():
        flash("Name already taken")
    elif Users.query.filter_by(email = request.form.get("email")).first():
        flash("Email already registered, log in instead")
        return redirect("login")
    else:
        if request.method == "POST":
            new_user = Users(
                name = request.form.get("name"),
                email = request.form.get("email"),
                password = flask_bcrypt.generate_password_hash(request.form.get("password"),10)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('profile'))
    return render_template("register.html")

@app.route("/sign In",methods=["GET","POST"])
def sign_in():
    if request.method == "POST":
        if not Users.query.filter_by(email = request.form.get("email")).first():
            flash("Email not registered, register instead")
            return redirect('register')
        remember = request.form.get("remember") == "on" 
    
        user = Users.query.filter_by(email= request.form.get("email")).first()
        if flask_bcrypt.check_password_hash(user.password,request.form.get("password")):
            login_user(user, remember=remember)
            return redirect(url_for('profile'))
        else:
            flash("Password Incorrect")
            return redirect(url_for('sign_in'))
    return render_template("sign_in.html")

login_manager.login_view = "sign_in" 

@app.route("/profile", methods = ["GET","POST"])
@login_required
def profile():
    tasks = Tasks.query.filter_by(user_id=current_user.get_id()).all()

    return render_template("profile.html",
                           user = current_user,logged_in = current_user.is_authenticated,
                           tasks = tasks,
                           num_task = len(tasks))

@app.route("/add task", methods = ["GET","POST"])
@login_required
def addtask():
    user = Users.query.get(current_user.id)
    if request.method == "POST":
        if request.form.get("start_time") and request.form.get("end_time"):
            new_task = Tasks(
                user=user,
                task = request.form.get("task"),
                start = convert_time_format(request.form.get("start_time")),
                end = convert_time_format(request.form.get("end_time")),
                everyday = request.form.get("everyday") == 'True',
                all_day = request.form.get("all_day") == 'True',
                date = date.today().strftime("%B %d, %Y"),
            )
        else:
             new_task = Tasks(
                user=user,
                task = request.form.get("task"),
                everyday = request.form.get("everyday") == 'True',
                all_day = request.form.get("all_day") == 'True',
                date = date.today().strftime("%B %d, %Y"),
            )
            
        db.session.add(new_task)
        db.session.commit()
        flash("You have succesfully added a new Task")
        return redirect(url_for('profile'))
    return render_template("profile.html",
                           user = current_user,logged_in = current_user.is_authenticated)


@app.route("/done/<int:task_id>", methods = ["GET","POST"])
def completed(task_id):
    task = Tasks.query.get(task_id)
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for('profile'))    

@app.route("/edit/<int:task_id>", methods = ["GET","POST"])
def edit(task_id):
    task = Tasks.query.get(task_id)
    task.task = request.form.get("task")
    if request.method =="POST":
        task.task = request.form["task"]
        task.start = convert_time_format(request.form.get("start_time"))
        task.end = convert_time_format(request.form.get("end_time"))
        task.everyday = request.form.get("everyday") == 'True'
        task.all_day = request.form.get("all_day") == 'True'
        db.session.commit()
        flash("Change Effected")

    return redirect(url_for('profile'))   



@app.route("/delete task/<int:task_id>", methods = ["GET","POST"])
def delete(task_id):
    task = Tasks.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task Succesfully Deleted")
    return redirect(url_for('profile'))    



@app.route("/log out")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)