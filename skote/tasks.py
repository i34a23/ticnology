from flask import Blueprint,render_template
# from flask_login import login_required

tasks = Blueprint('tasks',__name__,template_folder='templates',
    static_folder='static',)

@tasks.route('/tasks/list/')
def tasks_list():
    return render_template('tasks/tasks-list.html')

@tasks.route('/tasks/kanban/')
def tasks_kanban():
    return render_template('tasks/tasks-kanban.html')   

@tasks.route('/tasks/create/')
def tasks_create():
    return render_template('tasks/tasks-create.html')       