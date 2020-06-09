import os,json
import requests

from flask import Flask, render_template, jsonify, request, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from models import *

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# Check for environment variable
if not os.getenv("PATH"):
    raise RuntimeError("DATABASE_URL is not set")


# Set up database
engine = create_engine(("postgres://banxvrgczxjmut:d740f747285b25dc634c21ab86606fc7d944c74e71f521055fe9b207b4f404ab@ec2-54-86-170-8.compute-1.amazonaws.com:5432/d6v1s2rngr52aq"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["POST", "GET"])
#accessing website first brings to login page
def index():
    if session.get("user") is None:
        session["notes"]=[]
        return render_template("login.html")
    return render_template("index.html")

if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.run()

@app.route("/login", methods=["GET","POST"])
def login_process():
    session.clear()
    if request.method == 'POST':
        if not request.form.get("username"):
            return render_template("error.html",message="Did not enter valid username")
        if not request.form.get("passowrd"):
            return render_template("error.html",message="Did not enter valid password")
        else: 
            username = request.form.get("username")
            password = request.form.get("password")
        rows = db.execute("select * from users where username=:username", {"username": username})
        exist = rows.fetchone()
        if exist == None or not check_password_hash(result[2], password):
            return render_template("error.html", message='Invalid username or password')
        
        session['user'].append(result[1])
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout_process():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["POST", "GET"])
#link to register page 
def register_process():
    session.clear()
    if request_method == "POST":
        if not request.form.get("username"):
            return render_template("erorr.html",message="Username field required")
        if not request.form.get("password"):
            return render_template("error.html",message="Password field required")
        if not request.form.get("confirm"):
            return render_template("error.html",message='Confirm password field required')
        username = request.form.get('username')
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if not password == confirm:
            return render_template("error.html", message='Passowrd and confirm password do not match')
        check = db.execute("select * from users where username=:username", {"username":username}).fetchone
        if check:
            return render_template("error.html", message='Username already exists, please pick another')
        hashed = generate_password_hash(password,method='pbkdf2:sha256', salt_length=8)
        db.execute("INSERT into users(username, hash) values (:username, :passowrd)", {"username":username,"password":hashed})
        db.commit()
        flash('Account successfully created', 'info')
        return render_template("login.html")
    return render_template("registration.html")

@app.route("/search",  methods=["POST","GET"])
#from login page attempt to login 
def search():
    if session.get("user") is None:
        return render_template("login.html")
    #get username and password entered
    if request_method == "POST":
        if not request.form.get("book"):
            return render_template("error.html", message='Must provide a parameter')
        query = "%" + request.form.get("book") +"%"
        query = query.title()
        rows = db.execute("select isbn,title,author,year from books where isbn like :query or title like :query or author like :query limit 15", {"query":query})

        #check if exist in database 
        if rows.rowcount == 0:
            return render_template("error.html", message="Unable to find books that match your serach")

        #else successful login go to search.html
        books = rows.fetchall()

        return render_template("results.html", books=books)
    else:
        return render_template("login.html")

@app.route("/book/<isbn>", methods=["GET","POST"])
def book(isbn):
    if session.get("user") is None:
        return render_template("login.html")
    #if a review was submitted on book.html as a post method
    if request.method == 'POST':
        currentUser=session['user_id']
        rating = request.form.get("rating")
        rating = int(rating)
        comment = request.form.get("comment") 
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        bookId = row.fetchone() # (id,)
        bookId = bookId[0]     
        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})
        if row2.rowcount == 1:
            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn)
        db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": currentUser, 
                    "book_id": bookId, 
                    "comment": comment, 
                    "rating": rating})
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/book/" + isbn)

    else:
        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})
        #Get all info about book from data base, currently as a list of properties isbn etc 
        bookInfo = row.fetchall()
        #Get review statistics given a list of ISBNs from api.
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": 'g2vh3fkjeNtuH2f3DUA5A', "isbns": isbn})
        response = query.json()
        response = response['books'][0]
        #Combine results
        bookInfo.append(response)
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})
        #Get id from database
        book = row.fetchone()
        book = book[0]
        #Get book reviews on the specific book from own database
        results = db.execute("SELECT users.username, comment, rating, \
                            to_char(time, 'DD Mon YY - HH24:MI:SS') as time \
                            FROM users \
                            INNER JOIN reviews \
                            ON users.id = reviews.user_id \
                            WHERE book_id = :book \
                            ORDER BY time",
                            {"book": book})

        reviews = results.fetchall()
        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)

@app.route("/api/<isbn>", methods=['GET'])
def api_call(isbn):
    if session.get("user") is None:
            return render_template("login.html")
    # Retrieve book’s title, author, publication date, ISBN number, review count, and average score from database 
    row = db.execute("SELECT title, author, year, isbn, \
                    COUNT(reviews.id) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.id = reviews.book_id \
                    WHERE isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})

    # Error checking
    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book ISBN"}), 422

    # Fetch result from RowProxy    
    tmp = row.fetchone()
    
    # Convert to dict
    result = dict(tmp.items())

    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(
        result
    )