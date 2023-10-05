from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired, URL, NumberRange
from flask_ckeditor import CKEditorField


# WTForm for adding a cafe
class CreateCafeForm(FlaskForm):
    name = StringField("Cafe Name", validators=[DataRequired()])
    summary = StringField("Summarize your opinion about the cafe in a few words", validators=[DataRequired()])
    rating = IntegerField('What would you rate this cafe from 1 to 10?',
                          validators=[DataRequired(),
                                      NumberRange(min=1, max=10, message='Rating must be between 1 and 10.')])
    body = CKEditorField("Why did you give the cafe this rating? Be as specific as you like :)", validators=[DataRequired()])
    img_url = StringField("Add an image of the cafe (optional)", validators=[URL()])
    submit = SubmitField("Submit Post")


# Created a form to register new users
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


# Created a form to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


# Created a form to add comments
class CommentForm(FlaskForm):
    comment_text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")
