from flask import Blueprint,render_template
from flask_login import login_required

invoices = Blueprint('invoices',__name__,template_folder='templates',
    static_folder='static',)

@invoices.route('/invoices/list/')
@login_required
def invoices_list():
    return render_template('invoices/invoices-list.html')

@invoices.route('/invoices/details/')
@login_required
def invoices_details():
    return render_template('invoices/invoices-details.html')