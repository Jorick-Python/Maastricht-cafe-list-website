import smtplib
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from forms import CreateCafeForm, RegisterForm, LoginForm, CommentForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# For adding profile images to the comment section
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI","sqlite:///cafes.db")
db = SQLAlchemy()
db.init_app(app)


# CONFIGURE TABLES
class Cafe(db.Model):
    __tablename__ = "cafelist"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    contributor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    contributor_name = db.Column(db.String(100))  # Add contributor_name field
    # Create reference to the User object. The "cafes" refers to the cafes property in the User class.
    contributor = relationship("User", back_populates="cafes")
    name = db.Column(db.String(250), unique=True, nullable=False)
    summary = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250))
    rating = db.Column(db.Integer, nullable=False)
    # Parent relationship to the comments
    comments = relationship("Comment", back_populates="parent_cafe")


# Create a User table for all your registered users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # This will act like a list of Café objects attached to each User.
    # The "contributor" refers to the contributor property in the Cafe class.
    cafes = relationship("Cafe", back_populates="contributor")
    # Parent relationship: "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


# Create a table for the comments on the blog cafes
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # Child relationship:"users.id" The users refers to the tablename of the User class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # Child Relationship to the BlogPosts
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafelist.id"))
    parent_cafe = relationship("Cafe", back_populates="comments")


with app.app_context():
    db.create_all()


# Create an admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


def user_can_edit_cafe(func):
    @wraps(func)
    def decorated_function(cafe_id):
        cafe = Cafe.query.get_or_404(cafe_id)

        # Check if the current user is the contributor of the cafe post
        if current_user != cafe.contributor or current_user.id != 1:
            abort(403)  # Forbidden, as the user is not the contributor

        return func(cafe_id)

    return decorated_function


# Register new users into the User database
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        # Check if user email is already present in the database.
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for("cafelist"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('cafelist'))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('cafelist'))


@app.route('/')
def cafelist():
    result = db.session.execute(db.select(Cafe))
    cafes = result.scalars().all()
    return render_template("index.html", all_cafes=cafes, current_user=current_user)


# Added a POST method to be able to post comments
@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
def show_cafe(cafe_id):
    requested_cafe = db.get_or_404(Cafe, cafe_id)
    # Add the CommentForm to the route
    comment_form = CommentForm()
    # Only allow logged-in users to comment on cafes
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_cafe=requested_cafe
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("cafe.html", cafe=requested_cafe, current_user=current_user, form=comment_form)


# Used a decorator so only an admin user can create new cafes
@app.route("/new-cafe", methods=["GET", "POST"])
@login_required
def add_new_cafe():
    form = CreateCafeForm()
    if form.validate_on_submit():
        contributor_name = form.contributor_name.data or current_user.name  # Set default if None
        new_cafe = Cafe(
            name=form.name.data,
            summary=form.summary.data,
            body=form.body.data,
            img_url=form.img_url.data,
            contributor_name=contributor_name,
            date=date.today().strftime("%B %d, %Y"),
            rating=form.rating.data
        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for("cafelist"))
    return render_template("add-cafe.html", form=form, current_user=current_user)


# Used a decorator so only an admin user can edit a post
@app.route("/edit-cafe/<int:cafe_id>", methods=["GET", "POST"])
@login_required
def edit_cafe(cafe_id):
    cafe = db.get_or_404(Cafe, cafe_id)
    edit_form = CreateCafeForm(
        name=cafe.name,
        summary=cafe.summary,
        img_url=cafe.img_url,
        author=cafe.contributor,
        body=cafe.body,
        rating=cafe.rating
    )
    if edit_form.validate_on_submit():
        contributor_name = edit_form.contributor_name.data or current_user.name  # Set default if None
        cafe.name = edit_form.name.data
        cafe.summary = edit_form.summary.data
        cafe.img_url = edit_form.img_url.data
        cafe.contributor_name = contributor_name  # Update contributor's name
        cafe.body = edit_form.body.data
        cafe.rating = edit_form.rating.data
        db.session.commit()
        return redirect(url_for("show_cafe", cafe_id=cafe.id))
    return render_template("add-cafe.html", form=edit_form, is_edit=True, current_user=current_user)


# Used a decorator so only an admin user can delete a post
@app.route("/delete/<int:cafe_id>")
@admin_only
def delete_cafe(cafe_id):
    cafe_to_delete = db.get_or_404(Cafe, cafe_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    return redirect(url_for('cafelist'))


about = False
if about:
    @app.route("/about")
    def about():
        return render_template("about.html", current_user=current_user)

MAIL_ADDRESS = os.environ.get("EMAIL_KEY")
MAIL_APP_PW = os.environ.get("PASSWORD_KEY")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


#
#
def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(MAIL_ADDRESS, MAIL_APP_PW)
        connection.sendmail(MAIL_ADDRESS, MAIL_APP_PW, email_message)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
