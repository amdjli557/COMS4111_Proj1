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
from flask import Flask, session, request, render_template, g, redirect, Response

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
@app.route('/', methods = ["GET", "POST"])
def index():
  # DEBUG: this is debugging code to see what request looks like
  print(request.args)
  hname = None
  names = []

  #
  # example of a database query
  #
  if request.method == 'POST':
      hname = request.form.get('hname') 

        # Check if 'hname' exists
      if hname:  # Proceed only if the form has the 'hname' value
          hname_pattern = f"%{hname}%"
            
            # Use parameterized query to prevent SQL injection
          cursor = g.conn.execute("SELECT * FROM Hotels WHERE name LIKE %s", (hname_pattern,))
          for result in cursor:
              names.append(result)  # can also be accessed using result[0]
          cursor.close()

  return render_template("index.html", names=names, hname=hname)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/another')
def another():
  return render_template("anotherfile.html")


# Example of adding new data to the database

#@app.route('/search', methods=['POST'])
#def search():
  
#  if hname:  # Proceed only if the form has the 'hname' value
#    cursor = g.conn.execute("SELECT * FROM Hotels WHERE name LIKE ?", (hname,))
#    for result in cursor:
#        names.append(result)  # can also be accessed using result[0]
#    cursor.close()
#  return redirect('/')
#@app.route('/add', methods=['POST'])
#def add():
#  name = request.form['name']
#  print(name)
#  cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
#  g.conn.execute(text(cmd), name1 = name, name2 = name);
#  return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    uid = None
    if request.method == 'POST':
        uid = request.form.get('uid')
        session['uid'] = int(uid)
        return redirect('/user')
    return render_template("login.html", uid=uid)

@app.route('/user', methods=['GET', 'POST'])
def user():
    uid = session.get('uid')
    cursor = g.conn.execute("SELECT name FROM Users WHERE user_id = %s", (uid,))
    username = None
    for result in cursor:
        username = result['name']
    cursor.close()
    return render_template("user.html", uid=uid, username=username)

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
