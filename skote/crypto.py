from flask import Blueprint,render_template
from flask_login import login_required

crypto = Blueprint('crypto',__name__,template_folder='templates',
    static_folder='static',)

@crypto.route('/crypto/wallet/')
@login_required
def wallet():
    return render_template('crypto/crypto-wallet.html')

@crypto.route('/crypto/buysell/')
@login_required
def buysell():
    return render_template('crypto/crypto-buysell.html')    

@crypto.route('/crypto/exchange/')
@login_required
def exchange():
    return render_template('crypto/crypto-exchange.html')   

@crypto.route('/crypto/lending/')
@login_required
def lending():
    return render_template('crypto/crypto-lending.html')   

@crypto.route('/crypto/orders/')
@login_required
def orders():
    return render_template('crypto/crypto-orders.html')  

@crypto.route('/crypto/kyc/')
@login_required
def kyc():
    return render_template('crypto/crypto-kyc.html')    

@crypto.route('/crypto/ico-landing/')
@login_required
def ico_landing():
    return render_template('crypto/crypto-ico-landing.html')               
