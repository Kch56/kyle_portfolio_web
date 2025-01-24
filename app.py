from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail, Message

app = Flask(__name__)

# Configuring Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your mail server (Gmail in this case)
app.config['MAIL_PORT'] = 465  # For Gmail SSL
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'kylehampton949@gmail.com'  # Your email address
app.config['MAIL_PASSWORD'] = 'eqme fbeu azpl sebc'  # Your email password
app.config['MAIL_DEFAULT_SENDER'] = 'kylehampton949@gmail.com@gmail.com'

mail = Mail(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/resume')
def resume():
    return render_template('resume.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        msg = Message(f"New message from {name}",
                      recipients=["kylehampton949@gmail.com"])  # Your email address here
        msg.body = f"Message from: {name} ({email})\n\n{message}"

        try:
            mail.send(msg)
            return redirect(url_for('thank_you'))  # Redirect to a thank you page
        except Exception as e:
            return str(e)
    return render_template('contact.html')

@app.route('/thank-you')
def thank_you():
    return "Thank you for your message!"  # This can be a thank you page or redirect to home

if __name__ == '__main__':
    app.run(debug=True)
