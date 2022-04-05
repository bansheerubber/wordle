from flask import Flask, render_template, request
from solver import Knowledgebase, decode_input
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

solver = Knowledgebase()
guess = "arose"

users = {
	"me": generate_password_hash("password"),
}

@auth.verify_password
def verify_password(username, password):
	if username in users and check_password_hash(users.get(username), password):
		return username

def reset():
	global guess
	global solver
	
	solver = Knowledgebase()
	guess = "arose"

@app.route("/", methods = ["GET", "POST"])
@auth.login_required
def index():
	global guess
	global solver
	
	crash = "Nope"
	if request.method == 'POST':
		result = request.form.get("result", default="", type=str)
		reset_value = request.form.get("reset", default="", type=str)

		if reset_value != "":
			reset()
			return render_template("index.html", guess=guess, crash=crash)

		if result == "":
			crash = "Enter something idiot"
			return render_template("index.html", guess=guess, crash=crash)
		
		try:
			solver.add_knowledge(decode_input(result))
			guess = solver.guess()
		except Exception as e:
			print(e)
			reset()
			crash = "Yep"
	
	return render_template("index.html", guess=guess, crash=crash)

if __name__ == "__main__":
	app.run(host="0.0.0.0", port="8001")
