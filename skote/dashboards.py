from flask import Blueprint,render_template
from flask_login import login_required

dashboards = Blueprint('dashboards',__name__,template_folder='templates',
    static_folder='static',)

@dashboards.route('/')
@login_required
def index():
    return render_template('dashboards/index.html')    

@dashboards.route('/dashboard-saas/')
@login_required
def dashboard_saas():
    return render_template('dashboards/dashboard-saas.html')

@dashboards.route('/dashboard-crypto/')
@login_required
def dashboard_crypto():
    return render_template('dashboards/dashboard-crypto.html')    

@dashboards.route('/dashboard-blog/')
@login_required
def dashboard_blog():
    return render_template('dashboards/dashboard-blog.html')   

@dashboards.route('/dashboard-jobs/')
@login_required
def dashboard_jobs():
    return render_template('dashboards/dashboard-jobs.html')          