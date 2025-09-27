from flask import Blueprint,render_template
from flask_login import login_required

contacts = Blueprint('contacts',__name__,template_folder='templates',
    static_folder='static',)

@contacts.route('/contacts/users_grid/')
@login_required
def users_grid():
    return render_template('contacts/users-grid.html')

@contacts.route('/contacts/users_list/')
@login_required
def users_list():
    return render_template('contacts/users-list.html')    

@contacts.route('/contacts/contacts-profile/')
@login_required
def contacts_profile():
    return render_template('contacts/contacts-profile.html')       