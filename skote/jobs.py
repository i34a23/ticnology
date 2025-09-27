from flask import Blueprint,render_template
from flask_login import login_required

jobs = Blueprint('jobs',__name__,template_folder='templates',
    static_folder='static',)

@jobs.route('/jobs/list/')
@login_required
def jobs_list():
    return render_template('jobs/jobs-list.html')

@jobs.route('/jobs/grid/')
@login_required
def jobs_grid():
    return render_template('jobs/jobs-grid.html')    

@jobs.route('/jobs/apply/')
@login_required
def jobs_apply():
    return render_template('jobs/jobs-apply.html')       

@jobs.route('/jobs/details/')
@login_required
def jobs_details():
    return render_template('jobs/jobs-details.html')    

@jobs.route('/jobs/categories/')
@login_required
def jobs_categories():
    return render_template('jobs/jobs-categories.html')   

@jobs.route('/jobs/candidate-list/')
@login_required
def jobs_candidate_list():
    return render_template('jobs/candidate/candidate-list.html')   

@jobs.route('/jobs/candidate-overview/')
@login_required
def jobs_candidate_overview():
    return render_template('jobs/candidate/candidate-overview.html') 