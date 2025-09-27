from flask import Blueprint,render_template
from flask_login import login_required

blogs = Blueprint('blogs',__name__,template_folder='templates',
    static_folder='static',)

@blogs.route('/blogs/list/')
@login_required
def blogs_list():
    return render_template('blogs/blogs-list.html')

@blogs.route('/blogs/grid/')
@login_required
def blogs_grid():
    return render_template('blogs/blogs-grid.html')     

@blogs.route('/blogs/details/')
@login_required
def blogs_details():
    return render_template('blogs/blogs-details.html') 
    