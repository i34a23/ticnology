from flask import Blueprint,render_template
from flask_login import login_required

email = Blueprint('email',__name__,template_folder='templates',
    static_folder='static',)

@email.route('/email/inbox/')
@login_required
def email_inbox():
    return render_template('email/email-inbox.html')

@email.route('/email/read-email/')
@login_required
def email_read_email():
    return render_template('email/email-read-email.html')    

@email.route('/email/basic-action/')
@login_required
def email_basic_action():
    return render_template('email/email-basic-action.html')      

@email.route('/email/alert/')
@login_required
def email_alert():
    return render_template('email/email-alert.html')    

@email.route('/email/billing/')
@login_required
def email_billing():
    return render_template('email/email-billing.html')        