import os

from flask import Flask, render_template, request
from models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://banxvrgczxjmut:d740f747285b25dc634c21ab86606fc7d944c74e71f521055fe9b207b4f404ab@ec2-54-86-170-8.compute-1.amazonaws.com:5432/d6v1s2rngr52aq"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def main():
    db.create_all()

if __name__ == "__main__":
    with app.app_context(): #allows, on the command line, interaction with the flask application
        main() 