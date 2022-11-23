import re

from flask import flash, session, redirect
from functools import wraps

def validate(fields, request, uppercase=[], lowercase=[]):
    """Validates user input, returns field if valid, returns False if not"""

    valid_data = {}

    # Validates all fields
    for field in fields:

        # Ensure field was submitted
        if not request.form.get(field["name"]):
            flash("Missing " + field["label"], "alert-danger")
            return False

        # Standardise capitalisation for certain fields
        if field["name"] in uppercase:
            data = request.form.get(field["name"]).upper()
        elif field["name"] in lowercase:
            data = request.form.get(field["name"]).lower()
        else:
            data = request.form.get(field["name"])

        # Ensure input with lists are valid
        if field["type"] == "list":
            if data not in field["options"]:
                flash("Invalid " + field["label"], "alert-danger")
                return False

        # Ensure number inputs are valid
        if field["type"] == "number":

            # Ensure data is indeed a number
            if type(data) is not int or type(data) is not float:
                try:
                    data = float(data)
                except ValueError:
                    flash(field["label"] + " must be a number", "alert-danger")
                    return False

            # Ensure data is wihtin range
            if data < field["min"]:
                flash(field["label"] + " must be at least " + field["min"], "alert-danger")
                return False

            # Ensure data is integer:
            if field["step"] == 1:
                if data % 1 != 0:
                    flash(field["label"] + " must be an integer", "alert-danger")
                    return False
                else:
                    data = int(data)

        # Ensure email fields are valid
        if field["type"] == "email":
            if not re.search(".+@.+\..+", data):
                flash("Invalid email format for " + field["label"], "alert-danger")
                return False


        # Store field data into field dictionary
        valid_data[field["name"]] = data

    return valid_data


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Login Required!", "alert-danger")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def master_only(f):
    """
    Decorate routes so only master account has access.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") != 1:
            flash("Access Denied!", "alert-danger")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def two_decimal(value):
    """Format value as 2 decimal places"""
    return f"{value:.2f}"


def three_digit(value):
    """Format value as 3 digits"""
    return f"{value:0=3}"
