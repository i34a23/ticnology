from flask import Blueprint,render_template
from flask_login import login_required

projects = Blueprint('projects',__name__,template_folder='templates',
    static_folder='static',)

@projects.route('/projects/grid/')
@login_required
def projects_grid():
    return render_template('projects/projects-grid.html')

@projects.route('/projects/list/')
@login_required
def projects_list():
    return render_template('projects/projects-list.html')    

@projects.route('/projects/overview/')
@login_required
def projects_overview():
    return render_template('projects/projects-overview.html')

@projects.route('/projects/create/')
@login_required
def projects_create():
    return render_template('projects/projects-create.html')    