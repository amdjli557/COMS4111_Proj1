#!/usr/bin/env python3

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, session, request, render_template, g, redirect, Response, url_for
from datetime import datetime, date

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

app.secret_key = '4111'

# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "jz3858"
DB_PASSWORD = "935883608"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
#engine.execute("""DROP TABLE IF EXISTS test;""")
#engine.execute("""CREATE TABLE IF NOT EXISTS test (
#  id serial,
#  name text
#);""")
#engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/', methods=["GET", "POST"])
def index():
    hname = request.form.get('hname')
    star_rating = request.form.get('star_rating')
    user_id = session.get('uid')  # Get user_id if logged in
    hotels = []
    if request.method == 'POST':
        query = "SELECT hotel_id, name FROM Hotels WHERE 1=1"
        params = []

        if hname and hname.strip():
            query += " AND LOWER(name) LIKE LOWER(%s)"
            params.append(f"%{hname}%")

        if star_rating and star_rating.strip():
            query += " AND star_rating = %s"
            params.append(int(star_rating))

        cursor = g.conn.execute(query, params)
        for result in cursor:
            hotels.append({
                "hotel_id": result[0],
                "name": result[1]
            })
        cursor.close()

    return render_template("index.html", 
                         hotels=hotels, 
                         hname=hname, 
                         star_rating=star_rating,
                         user_id=user_id) 

@app.route('/hotel/<int:hotel_id>', methods=['GET'])
def hotel_details(hotel_id):
    user_id = session.get('uid')  # Get user_id from session
    
    # Fetch hotel details from the database
    cursor = g.conn.execute("""
        SELECT name, address, email FROM Hotels WHERE hotel_id = %s;
    """, (hotel_id,))
    hotel = cursor.fetchone()
    if hotel:
        hotel = dict(hotel)
        hotel['hotel_id'] = hotel_id  # Add hotel_id to the hotel dict

    # Fetch reviews for the hotel
    cursor = g.conn.execute("""
        SELECT uwr.content, uwr.rating, uwr.likes, uwr.time 
        FROM Hotel_Has_Reviews AS hhr, User_Writes_Reviews AS uwr 
        WHERE hhr.hotel_id = %s AND hhr.review_id = uwr.review_id;
    """, (hotel_id,))
    reviews = cursor.fetchall()

    # Fetch rooms for the hotel
    cursor = g.conn.execute("""
        SELECT * 
        FROM Hotel_Contains_Rooms AS hcr 
        WHERE hotel_id = %s;
    """, (hotel_id,))
    rooms = cursor.fetchall()

    cursor.close()

    return render_template('hotel_details.html', 
                         hotel=hotel, 
                         reviews=reviews, 
                         rooms=rooms,
                         user_id=user_id) 


@app.route('/login', methods=['GET', 'POST'])
def login():
    uid = None
    if request.method == 'POST':
        uid = request.form.get('uid')
        session['uid'] = int(uid)
        return redirect('/user')
    return render_template("login.html", uid=uid)

@app.route('/user')
def user():
    uid = session.get('uid')
    if not uid:
        return redirect('/login')
        
    # Get username
    cursor = g.conn.execute("SELECT name FROM Users WHERE user_id = %s", (uid,))
    username = None
    for result in cursor:
        username = result['name']
        
    # Get all bookings for the user
    cursor = g.conn.execute("""
        SELECT ub.confirmation_code, ub.check_in, ub.check_out, 
               ub.guest_number, ub.price, ub.past, ub.upcoming,
               h.name as hotel_name
        FROM User_Owns_Bookings ub
        JOIN Hotels h ON ub.hotel_id = h.hotel_id
        WHERE ub.user_id = %s
        ORDER BY ub.check_in DESC
    """, (uid,))
    bookings = cursor.fetchall()
    cursor.close()

    return render_template("user.html", 
                         uid=uid, 
                         username=username,
                         bookings=bookings)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    uid = session.get('uid')
    if not uid:
        return redirect('/login')

    # Handle both POST (from form) and GET (from URL) methods
    confirmation_code = request.form.get('confirmation_code')  # For POST
    if not confirmation_code:
        confirmation_code = request.args.get('confirmation_code')  # For GET

    booking_details = None

    if confirmation_code:
        try:
            confirmation_code = int(confirmation_code)
            # Modified query to use LEFT JOIN and get booking details even without room assignment
            query = """
                SELECT ub.confirmation_code, ub.check_in, ub.check_out, 
                       ub.guest_number, ub.price, h.name AS hotel_name,
                       h.hotel_id
                FROM User_Owns_Bookings ub
                JOIN Hotels h ON ub.hotel_id = h.hotel_id
                WHERE ub.confirmation_code = %s
                AND ub.user_id = %s
            """
            
            cursor = g.conn.execute(query, (confirmation_code, uid))
            result = cursor.fetchone()
            
            if result:
                booking_details = {
                    'check_in': result['check_in'],
                    'check_out': result['check_out'],
                    'guest_number': result['guest_number'],
                    'price': result['price'],
                    'hotel_name': result['hotel_name'],
                    'confirmation_code': result['confirmation_code'],
                    'hotel_id': result['hotel_id']
                }

            cursor.close()

        except ValueError:
            return "Invalid confirmation code format"

    return render_template("booking.html", booking_details=booking_details)

@app.route('/saved_rooms')
def saved_rooms():
    uid = session.get('uid')
    if not uid:
        return redirect('/login')
        
    query = """
        SELECT h.name as hotel_name, hcr.room_type, hcr.features, hcr.room_id
        FROM User_Saves_Rooms usr
        JOIN Hotel_Contains_Rooms hcr ON usr.room_id = hcr.room_id
        JOIN Hotels h ON hcr.hotel_id = h.hotel_id
        WHERE usr.user_id = %s
    """
    
    cursor = g.conn.execute(query, (uid,))
    saved_rooms = []
    for result in cursor:
        saved_rooms.append({
            'hotel_name': result['hotel_name'],
            'room_type': result['room_type'],
            'features': result['features'],
            'room_id': result['room_id']
        })
    cursor.close()
    
    return render_template('saved_rooms.html', saved_rooms=saved_rooms)

@app.route('/user_reviews')
def user_reviews():
    uid = session.get('uid')
    if not uid:
        return redirect('/login')
        
    query = """
        SELECT uwr.review_id, uwr.content, uwr.rating, uwr.likes, uwr.time,
               h.name as hotel_name
        FROM User_Writes_Reviews uwr
        JOIN Hotel_Has_Reviews hhr ON uwr.review_id = hhr.review_id
        JOIN Hotels h ON hhr.hotel_id = h.hotel_id
        WHERE uwr.user_id = %s
        ORDER BY uwr.time DESC
    """
    
    cursor = g.conn.execute(query, (uid,))
    reviews = []
    for result in cursor:
        reviews.append({
            'review_id': result['review_id'],
            'content': result['content'],
            'rating': result['rating'],
            'likes': result['likes'],
            'time': result['time'],
            'hotel_name': result['hotel_name']
        })
    cursor.close()
    
    return render_template('user_reviews.html', reviews=reviews)

@app.route('/add_review/<int:confirmation_code>', methods=['GET', 'POST'])
def add_review(confirmation_code):
    uid = session.get('uid')
    if not uid:
        return redirect('/login')

    if request.method == 'POST':
        content = request.form.get('content')
        rating = request.form.get('rating')
        
        if content and rating:
            try:
                # Get the hotel_id from the booking
                cursor = g.conn.execute("""
                    SELECT DISTINCT h.hotel_id 
                    FROM Room_Generates_Bookings rgb
                    JOIN Hotels h ON rgb.hotel_id = h.hotel_id
                    WHERE rgb.confirmation_code = %s
                """, (confirmation_code,))
                result = cursor.fetchone()
                
                if result:
                    hotel_id = result[0]
                    
                    # Get the next review_id
                    cursor = g.conn.execute("SELECT MAX(review_id) as max_id FROM User_Writes_Reviews")
                    result = cursor.fetchone()
                    new_review_id = (result[0] or 0) + 1

                    # Insert the review
                    g.conn.execute("""
                        INSERT INTO User_Writes_Reviews (review_id, user_id, content, rating, likes, time)
                        VALUES (%s, %s, %s, %s, 0, CURRENT_DATE)
                    """, (new_review_id, uid, content, rating))

                    # Link review to hotel
                    g.conn.execute("""
                        INSERT INTO Hotel_Has_Reviews (hotel_id, review_id)
                        VALUES (%s, %s)
                    """, (hotel_id, new_review_id))

                    # Redirect to the confirmation page
                    return redirect(url_for('review_submitted'))
            except Exception as e:
                print(f"Error adding review: {e}")
                return "Error adding review. Please try again."

    # For GET request, get hotel info for the form
    cursor = g.conn.execute("""
        SELECT DISTINCT h.name as hotel_name
        FROM Room_Generates_Bookings rgb
        JOIN Hotels h ON rgb.hotel_id = h.hotel_id
        WHERE rgb.confirmation_code = %s
    """, (confirmation_code,))
    hotel_info = cursor.fetchone()
    cursor.close()

    return render_template('add_review.html', 
                         confirmation_code=confirmation_code,
                         hotel_info=hotel_info)

@app.route('/review_submitted')
def review_submitted():
    return render_template('review_submitted.html')

@app.route('/make_booking/<int:hotel_id>/<int:room_id>', methods=['GET', 'POST'])
def make_booking(hotel_id, room_id):
    uid = session.get('uid')
    if not uid:
        return redirect('/login')
    if request.method == 'POST':
        try:
            check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d').date()
            guest_number = int(request.form['guest_number'])
            price = float(request.form['price'])
            
            # Determine if booking is past or upcoming
            today = date.today()
            is_past = check_in < today
            is_upcoming = check_in >= today

            # Get the next confirmation code
            cursor = g.conn.execute("SELECT MAX(confirmation_code) as max_code FROM User_Owns_Bookings")
            result = cursor.fetchone()
            new_confirmation_code = (result[0] or 100) + 1

            # First insert the booking with hotel_id
            g.conn.execute("""
                INSERT INTO User_Owns_Bookings 
                (confirmation_code, check_in, check_out, guest_number, price, 
                 past, upcoming, user_id, hotel_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_confirmation_code, check_in, check_out, guest_number, price, 
                 is_past, is_upcoming, uid, hotel_id))

            g.conn.execute("""
                INSERT INTO Room_Generates_Bookings 
                (confirmation_code, room_id, time, hotel_id)
                VALUES (%s, %s, CURRENT_DATE, %s)
            """, (new_confirmation_code, room_id, hotel_id))

            # Update room availability
            g.conn.execute("""
                UPDATE Hotel_Contains_Rooms 
                SET availability = false 
                WHERE room_id = %s
            """, (room_id,))

            return redirect(url_for('booking_confirmed', confirmation_code=new_confirmation_code))
            
        except Exception as e:
            print(f"Error making booking: {e}")
            return "Error making booking. Please try again."

    # For GET request, get hotel info
    cursor = g.conn.execute("SELECT name FROM Hotels WHERE hotel_id = %s", (hotel_id,))
    hotel = cursor.fetchone()
    cursor.close()

    return render_template('make_booking.html', hotel=hotel, hotel_id=hotel_id, room_id=room_id)


@app.route('/booking_confirmed/<int:confirmation_code>')
def booking_confirmed(confirmation_code):
    uid = session.get('uid')
    if not uid:
        return redirect('/login')

    # Get booking details
    cursor = g.conn.execute("""
        SELECT uob.*, h.name as hotel_name
        FROM User_Owns_Bookings uob
        JOIN Hotels h ON uob.hotel_id = h.hotel_id
        WHERE uob.confirmation_code = %s AND uob.user_id = %s
    """, (confirmation_code, uid))
    
    booking = cursor.fetchone()
    cursor.close()

    return render_template('booking_confirmed.html', booking=booking)


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    #app.run(host=HOST, port=PORT, debug=debug, threaded=threaded, ssl_context=('certificate.crt', 'private.key'))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
