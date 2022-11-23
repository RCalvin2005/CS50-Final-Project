import re
import os
import pytz

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from uuid import uuid4
from flask_mail import Mail, Message
from dotenv import load_dotenv
from datetime import datetime, timedelta

from helpers import validate, login_required, master_only, two_decimal, three_digit

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["two_decimal"] = two_decimal
app.jinja_env.filters["three_digit"] = three_digit

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///walet.db")

# https://www.realpythonproject.com/3-ways-to-store-and-read-credentials-locally-in-python/
load_dotenv()

# Make sure constants from environment are set
if not os.environ.get("MAIL_DEFAULT_SENDER_NAME"):
    raise RuntimeError("MAIL_DEFAULT_SENDER_NAME not set")

if not os.environ.get("MAIL_DEFAULT_SENDER_EMAIL"):
    raise RuntimeError("MAIL_DEFAULT_SENDER_EMAIL not set")

if not os.environ.get("MAIL_USERNAME"):
    raise RuntimeError("MAIL_USERNAME not set")

if not os.environ.get("MAIL_PASSWORD"):
    raise RuntimeError("MAIL_PASSWORD not set")

if not os.environ.get("MASTER_PASSWORD"):
    raise RuntimeError("MASTER_PASSWORD not set")

# Configure Flask Mail
app.config["MAIL_DEFAULT_SENDER"] = (os.environ.get("MAIL_DEFAULT_SENDER_NAME"), os.environ.get("MAIL_DEFAULT_SENDER_EMAIL"))
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_PORT"] = 587
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_USE_TLS"] = True
mail = Mail(app)

# Define columns in purchase table
shapes = ["bowl", "triangle", "oval", "fragment"]
feathers = ["clean", "light", "medium", "heavy"]
colors = ["A", "B", "C", "D"]
purchase_columns = [
    {"name": "date", "label": "Date", "type": "date"},
    {"name": "supplier", "label": "Supplier", "type": "text"},
    {"name": "supplier_code", "label": "Supplier Code", "type": "text"},
    {"name": "purchase_code", "label": "Purchase Code", "type": "text"},
    {"name": "shape", "label": "Shape", "type": "list", "options": shapes},
    {"name": "feather", "label": "Feathers", "type": "list", "options": feathers},
    {"name": "color", "label": "Color Grade", "type": "list", "options": colors},
    {"name": "mass", "label": "Mass", "type": "number", "min": 0, "step": "any"},
    {"name": "pieces", "label": "Pieces", "type": "number", "min": 1, "step": 1}
]
for column in purchase_columns:
    if column["type"] == "number":
        column["filter"] = False
        column["align"] = "text-end"
    else:
        column["filter"] = True
        column["align"] = "text-start"

# Define lists for validation
uppercase = ["supplier_code", "purchase_code", "production_code", "color"]
lowercase = ["shape", "feather"]

# Set local timezone
TZ = pytz.timezone("Asia/Jakarta")

# Initialise master account
admins = db.execute("SELECT * FROM admins")

# Creates master account if admins table is empty
if len(admins) == 0:
    db.execute("INSERT INTO admins (name, username, email, password_hash, account_hash) VALUES(?, ?, ?, ?, ?)",
        "Master Account", "Master", "bot.rcalvin2005@gmail.com", generate_password_hash(os.environ.get("MASTER_PASSWORD")), uuid4().hex
        )


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Display purchases database"""

    purchases = db.execute("SELECT * FROM purchases JOIN admins ON purchases.admin_id = admins.admin_id ORDER BY date")
    total = db.execute("SELECT SUM(mass), SUM(pieces) FROM purchases")[0]

    if total["SUM(mass)"] == None:
        total["SUM(mass)"] = 0

    if total["SUM(pieces)"] == None:
        total["SUM(pieces)"] = 0

    return render_template("index.html", purchases=purchases, total=total, columns=purchase_columns)


@app.route("/edit_purchase", methods=["GET", "POST"])
@login_required
def edit_purchase():
    """Allows admins to edit purchase table"""

    # Starts edit process
    if request.method == "POST":

        # Validates user input
        data = validate(purchase_columns, request, uppercase, lowercase)

        if data == False:
            return redirect("/edit_purchase")

        # Prevent race conditions
        db.execute("BEGIN TRANSACTION")

        edit_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

        # Store field data into database
        id = request.form.get("id")
        if not id:
            flash("Edit Failed!", "alert-danger")
            return redirect("/edit_purchase")

        for field in data:
            try:
                db.execute("UPDATE purchases SET ? = ? WHERE id = ?", field, data[field], id)
            except RuntimeError:
                flash("Edit Failed! Please try again after a few seconds", "alert-danger")
                return redirect("/edit_purchase")

        try:
            db.execute("UPDATE purchases SET admin_id = ?, edit_time = ? WHERE id = ?", session["user_id"], edit_time, id)
        except RuntimeError:
            flash("Edit Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/edit_purchase")

        db.execute("COMMIT")

        flash("Edit Succesful!", "alert-success")
        return redirect("/edit_purchase")

    # Renders editable database table
    else:

        purchases = db.execute("SELECT * FROM purchases JOIN admins ON purchases.admin_id = admins.admin_id ORDER BY date")
        total = db.execute("SELECT SUM(mass), SUM(pieces) FROM purchases")[0]

        if total["SUM(mass)"] == None:
            total["SUM(mass)"] = 0

        if total["SUM(pieces)"] == None:
            total["SUM(pieces)"] = 0

        return render_template("edit_purchase.html", purchases=purchases, total=total, columns=purchase_columns)


@app.route("/delete_purchase", methods=["POST"])
@login_required
def delete_purchase():
    """Deletes purchase entry and creates backup for restoration"""

    # Deletes table row
    if request.method == "POST":

        id = request.form.get("id")
        if not id:
            flash("Delete Failed!", "alert-danger")
            return redirect("/edit_purchase")

        rows = db.execute("SELECT * FROM purchases WHERE id = ?", id)

        if len(rows) != 1:
            flash("Delete Failed!", "alert-danger")
            return redirect("/edit_purchase")
        else:
            entry = rows[0]

        # Prevent race conditions
        db.execute("BEGIN TRANSACTION")

        # Store backup of entry
        try:
            db.execute("INSERT INTO deleted_purchases (id) VALUES(?)", id)
        except RuntimeError:
            flash("Delete Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/edit_purchase")

        for field in entry:
            try:
                db.execute("UPDATE deleted_purchases SET ? = ? WHERE id = ?", field, entry[field], id)
            except RuntimeError:
                flash("Delete Failed! Please try again after a few seconds", "alert-danger")
                return redirect("/edit_purchase")

        # Keeps tracks of who deleted
        edit_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

        try:
            db.execute("UPDATE deleted_purchases SET admin_id = ?, edit_time = ? WHERE id = ?", session["user_id"], edit_time, id)
        except RuntimeError:
            flash("Delete Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/edit_purchase")

        db.execute("COMMIT")

        # Deletes entry
        db.execute("DELETE FROM purchases WHERE id = ?", id)
        flash("Entry Deleted!", "alert-warning")

    return redirect("/edit_purchase")


@app.route("/restore_purchase", methods=["GET", "POST"])
@login_required
def restore():
    """Shows deleted entries and allows admins to restore them"""

    # Start restoration process
    if request.method == "POST":

        # Validates user input
        data = validate(purchase_columns, request, uppercase, lowercase)

        if data == False:
            return redirect("/restore_purchase")

        # Prevent race conditions
        db.execute("BEGIN TRANSACTION")

        edit_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

        id = request.form.get("id")
        if not id:
            flash("Restoration Failed!", "alert-danger")
            return redirect("/restore_purchase")

        # Restore entry into main database
        try:
            db.execute("INSERT INTO purchases (id) VALUES(?)", id)
        except RuntimeError:
            flash("Restoration Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/restore_purchase")

        for field in data:
            try:
                db.execute("UPDATE purchases SET ? = ? WHERE id = ?", field, data[field], id)
            except RuntimeError:
                flash("Restoration Failed! Please try again after a few seconds", "alert-danger")
                return redirect("/restore_purchase")

        try:
            db.execute("UPDATE purchases SET admin_id = ?, edit_time = ? WHERE id = ?", session["user_id"], edit_time, id)
        except RuntimeError:
            flash("Restoration Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/restore_purchase")

        db.execute("DELETE FROM deleted_purchases WHERE id = ?", id)

        db.execute("COMMIT")

        flash("Restoration Succesful!", "alert-success")
        return redirect("/edit_purchase")

    else:
        entries = db.execute("SELECT * FROM deleted_purchases JOIN admins ON deleted_purchases.admin_id = admins.admin_id ORDER BY date")

        return render_template("restore_purchase.html", purchases=entries, columns=purchase_columns)


@app.route("/permanent_delete", methods=["POST"])
@master_only
def permanent_delete():

    id = request.form.get("id")
    if not id:
        flash("Delete Failed!", "alert-danger")
        return redirect("/edit_purchase")

    db.execute("DELETE FROM deleted_purchases WHERE id = ?", id)

    flash("Entry Permanently Deleted!", "alert-warning")
    return redirect("/restore_purchase")


@app.route("/input_purchase", methods=["GET", "POST"])
@login_required
def input_purchase():
    """Input Purchase Data"""

    # Start input process
    if request.method == "POST":

        # Validates user input
        data = validate(purchase_columns, request, uppercase, lowercase)

        if data == False:
            return redirect("/input_purchase")

        # Prevent race conditions
        db.execute("BEGIN TRANSACTION")

        # Store field data into database
        try:
            id = db.execute("INSERT INTO purchases DEFAULT VALUES")
        except RuntimeError:
            flash("Input Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/input_purchase")

        for field in data:
            try:
                db.execute("UPDATE purchases SET ? = ? WHERE id = ?", field, data[field], id)
            except RuntimeError:
                flash("Input Failed! Please try again after a few seconds", "alert-danger")
                return redirect("/input_purchase")

        # Keep tracks of who made changes
        edit_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

        try:
            db.execute("UPDATE purchases SET admin_id = ?, edit_time = ? WHERE id = ?", session["user_id"], edit_time, id)
        except RuntimeError:
            flash("Edit Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/")

        db.execute("COMMIT")

        flash("Input Succesful!", "alert-success")
        return redirect("/")

    # Render input purchase page
    else:
        return render_template("input_purchase.html", fields=purchase_columns)


@app.route("/purchase_reports")
def purchase_reports():
    """Display purchase table with specific filter option"""

    labels = {
        "supplier": "Supplier",
        "purchase_code": "Purchase Code",
        "shape": "Shape",
    }

    filter = request.args.get("filter")
    purchases = db.execute("SELECT * FROM purchases")
    total = db.execute("SELECT SUM(mass), SUM(pieces) FROM purchases")[0]

    if total["SUM(mass)"] == None:
        total["SUM(mass)"] = 0

    if total["SUM(pieces)"] == None:
        total["SUM(pieces)"] = 0

    return render_template("purchase_reports.html", filter=filter, label=labels[filter], purchases=purchases, total=total, columns=purchase_columns)


@app.route("/purchase_summary")
def purchase_summary():
    """Summarises purchases by shape, feathers, and color"""

    # Define labels and column/row headings of the tables
    shapes_col = ["bowl", "triangle", "oval", "fragment", "Total Mass"]
    feathers_col = ["clean", "light", "medium", "heavy", "Total Mass"]
    colors_tables = [
            {"label": "Purchase Summary", "key": "all"},
            {"label": "Color Grade A Purchase Summary", "key": "A"},
            {"label": "Color Grade B Purchase Summary", "key": "B"},
            {"label": "Color Grade C Purchase Summary", "key": "C"},
            {"label": "Color Grade D Purchase Summary", "key": "D"},
        ]

    summary = {}
    for color in colors_tables:
        color_key = color["key"]
        summary[color_key] = {}

        for shape in shapes_col:
            summary[color_key][shape] = {}

            for feather in feathers_col:

                if shape == "Total Mass" and feather == "Total Mass":
                    # Query database for grand total
                    if color_key == "all":
                        row = db.execute("SELECT SUM(mass) FROM purchases")[0]
                    else:
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE color = ?", color_key)[0]

                elif shape == "Total Mass":
                    # Query database for feather total
                    if color_key == "all":
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE feather = ?", feather)[0]
                    else:
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE color = ? AND feather = ?", color_key, feather)[0]

                elif feather == "Total Mass":
                    # Query database for shape total
                    if color_key == "all":
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE shape = ?", shape)[0]
                    else:
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE color = ? AND shape = ?", color_key, shape)[0]

                else:
                    # Query database for sum per shape & feather
                    if color_key == "all":
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE shape = ? AND feather = ?", shape, feather)[0]
                    else:
                        row = db.execute("SELECT SUM(mass) FROM purchases WHERE color = ? AND shape = ? AND feather = ?", color_key, shape, feather)[0]

                # Store sum in dictionary
                if row["SUM(mass)"] == None:
                    summary[color_key][shape][feather] = 0
                else:
                    summary[color_key][shape][feather] = row["SUM(mass)"]

    return render_template("purchase_summary.html", summary=summary, shapes=shapes_col, feathers=feathers_col, colors=colors_tables)


@app.route("/admins", methods=["GET", "POST"])
@login_required
def admins():
    """Display admins management, and edit admins"""

    columns = [
        {"name": "admin_id", "label": "ID"},
        {"name": "name", "label": "Name"},
        {"name": "username", "label": "Username"},
        {"name": "email", "label": "Email"}
    ]

    admins = db.execute("SELECT * FROM admins")

    return render_template("admins.html", admins=admins, columns=columns)


@app.route("/register_admin", methods=["GET", "POST"])
@master_only
def register_admin():
    """Registers new admin"""

    admin_fields = [
        {"name": "name", "label": "Name", "type": "text"},
        {"name": "username", "label": "Username", "type": "text"},
        {"name": "email", "label": "Email", "type": "email"},
    ]

    # Starts registration process
    if request.method == "POST":

        # Ensures fields input is valid
        data = validate(admin_fields, request)

        if data == False:
            return redirect("/register_admin")

        name = data["name"]
        username = data["username"]
        email = data["email"]

        # Prevent race conditions
        db.execute("BEGIN TRANSACTION")

        # Ensures username does not already exist
        rows = db.execute("SELECT * FROM admins WHERE username = ?", username)

        if len(rows) != 0:
            flash("Username already exists", "alert-danger")
            return redirect("/register_admin")

        # Generate random account hash and password hash
        account_hash = uuid4().hex
        password_hash = generate_password_hash(uuid4().hex)

        # Stores new admin into database
        try:
            db.execute("INSERT INTO admins (name, username, email, password_hash, account_hash) VALUES(?, ?, ?, ?, ?)",
                name, username, email, password_hash, account_hash
                )
        except RuntimeError:
            flash("Registration Failed! Please try again after a few seconds", "alert-danger")
            return redirect("/register_admin")

        # Construct email for account activation and password setting
        msg = Message("New Admin Account Activation", recipients=[email])

        # https://stackoverflow.com/questions/11078264/how-to-get-rid-of-show-trimmed-content-in-gmail-html-emails
        msg.html = render_template("activation_email.html", name=name, username=username, account_hash=account_hash, random=datetime.now())

        mail.send(msg)

        db.execute("COMMIT")

        flash("Admin added!", "alert-success")
        return redirect("/admins")

    # Renders registration form
    else:
        return render_template("/register_admin.html", fields=admin_fields)


@app.route("/delete_admin", methods=["POST"])
@master_only
def delete_admin():
    """Deletes admin entry"""

    # Deletes table row
    if request.method == "POST":

        id = request.form.get("admin_id")
        db.execute("DELETE FROM admins WHERE admin_id == ?", id)
        flash("Entry Deleted!", "alert-warning")

    return redirect("/admins")


@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    """Activates new admin accounts & set password"""

    # Starts password setting process
    if request.method == "POST":

        rows = db.execute("SELECT * FROM admins WHERE admin_id= ?", request.form.get("admin_id"))

        route = "/set_password?acc=" + request.form.get("account_hash")

        # Failsafe to ensure no disabled inputs are altered
        if len(rows) != 1:
            flash("Invalid Account!", "alert-danger")
            return redirect("/")
        else:
            admin = rows[0]

        if admin['account_hash'] != request.form.get("account_hash"):
            flash("Invalid Account!", "alert-danger")
            return redirect(route)

        if admin['name'] != request.form.get("name"):
            flash("Invalid Account! 2", "alert-danger")
            return redirect(route)

        if admin['username'] != request.form.get("username"):
            flash("Invalid Account!", "alert-danger")
            return redirect(route)

        if admin['email'] != request.form.get("email"):
            flash("Invalid Account!", "alert-danger")
            return redirect(route)

        # Ensure passwords & confirmation are submitted
        if not request.form.get("password"):
            flash("Missing password!", "alert-danger")
            return redirect(route)

        if not request.form.get("confirmation"):
            flash("Missing confirmation!", "alert-danger")
            return redirect(route)

        # Ensure passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match!", "alert-danger")
            return redirect(route)

        # Store new password into database
        db.execute("UPDATE admins SET password_hash = ? WHERE admin_id = ?", generate_password_hash(request.form.get("password")), request.form.get("admin_id"))

        # Generate new account hash so link is one-time use
        db.execute("UPDATE admins SET account_hash = ? WHERE admin_id = ?", uuid4().hex, request.form.get("admin_id"))

        session['user_id'] = admin['admin_id']

        flash("Password Set!", "alert-success")

        return redirect("/")

    # Renders account activation page
    else:

        # Get admin data from account hash
        account_hash = request.args.get("acc")
        rows = db.execute("SELECT * FROM admins WHERE account_hash = ?", account_hash)

        # Ensure admin exists
        if len(rows) != 1:
            flash("Invalid Link!", "alert-danger")
            return redirect("/")
        else:
            admin = rows[0]

        admin_fields = [
                {"name": "name", "label": "Name", "type": "text", "value": admin['name']},
                {"name": "username", "label": "Username", "type": "text", "value": admin['username']},
                {"name": "email", "label": "Email", "type": "email", "value": admin['email']},
                {"name": "password", "label": "Password", "type": "password"},
                {"name": "confirmation", "label": "Confirm Password", "type": "password"},
            ]

        return render_template("set_password.html", fields=admin_fields, admin_id=admin['admin_id'], account_hash=account_hash)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login for Admins"""

    # Starts login process
    if request.method == "POST":

        # Ensures username & password is submitted
        if not request.form.get("username"):
            flash("Missing Username", "alert-danger")
            return redirect("/login")

        if not request.form.get("password"):
            flash("Missing Password", "alert-danger")
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM admins WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            flash("Invalid Username and/or Password", "alert-danger")
            return redirect("/login")

        # Forget any user id
        session.clear()

        # Remember which user has logged in
        session["user_id"] = rows[0]["admin_id"]

        # Redirect to homepage
        flash("Log In Successful", "alert-success")
        return redirect("/")

    # Renders login page
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    """Reset User Password by Email"""

    admin_fields = [
        {"name": "name", "label": "Name", "type": "text"},
        {"name": "username", "label": "Username", "type": "text"},
        {"name": "email", "label": "Email", "type": "email"},
    ]

    # Starts password reset process
    if request.method == "POST":

        # Ensures fields input is valid
        data = validate(admin_fields, request)

        if data == False:
            return redirect("/reset_password")

        name = data["name"]
        username = data["username"]
        email = data["email"]

        # Ensures name, username and email matches
        rows = db.execute("SELECT * FROM admins WHERE name = ? AND username = ? and email = ?", name, username, email)

        if len(rows) != 1:
            flash("Invalid Name and/or Username and/or Email", "alert-danger")
            return redirect("/reset_password")
        else:
            account_hash = rows[0]["account_hash"]

        # Check if on cooldown
        if session.get("cooldown"):
             if datetime.now() < session["cooldown"]:
                remaining = session["cooldown"] - datetime.now()
                flash("Please wait " + str(remaining.seconds) + " seconds", "alert-danger")
                return redirect("/reset_password")

        # Reset cooldown timer
        session["cooldown"] = datetime.now() + timedelta(minutes=1)

        # Construct email for password reset
        msg = Message("Reset Account Password", recipients=[email])

        # https://stackoverflow.com/questions/11078264/how-to-get-rid-of-show-trimmed-content-in-gmail-html-emails
        msg.html = render_template("password_reset_email.html", name=name, username=username, account_hash=account_hash, random=datetime.now())

        mail.send(msg)

        flash("Recovery Email Sent!", "alert-success")
        return redirect("/reset_password")

    # Renders registration form
    else:
        return render_template("/reset_password.html", fields=admin_fields)