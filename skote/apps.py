from flask import Blueprint,render_template
from flask_login import login_required

apps = Blueprint('apps',__name__,template_folder='templates',
    static_folder='static',)

@apps.route('/apps/calendar_tui/')
@login_required
def calendar_tui():
    return render_template('apps/calendar_tui.html')

@apps.route('/apps/calendar_full/')
@login_required
def calendar_full():
    return render_template('apps/calendar_full.html')    

@apps.route('/apps/chat/')
@login_required
def chat():
    return render_template('apps/chat.html')     

@apps.route('/apps/filemanager/')
@login_required
def filemanager():
    return render_template('apps/filemanager.html')