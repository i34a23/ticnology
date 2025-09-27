from flask import Blueprint,render_template
from flask_login import login_required

layouts = Blueprint('layouts',__name__,template_folder='templates',
    static_folder='static',)

#Vertical Layout
@layouts.route('/layouts/vertical/light_sidebar')
@login_required
def layouts_vertical_light_sidebar():
    return render_template('layouts/vertical/layouts-light-sidebar.html')

@layouts.route('/layouts/vertical/compact_sidebar')
@login_required
def layouts_vertical_compact_sidebar():
    return render_template('layouts/vertical/layouts-compact-sidebar.html')  

@layouts.route('/layouts/vertical/icon_sidebar')
@login_required
def layouts_vertical_icon_sidebar():
    return render_template('layouts/vertical/layouts-icon-sidebar.html')    

@layouts.route('/layouts/vertical/boxed_sidebar')
@login_required
def layouts_vertical_boxed_sidebar():
    return render_template('layouts/vertical/layouts-boxed-sidebar.html')   

@layouts.route('/layouts/vertical/preloader')
@login_required
def layouts_vertical_preloader():
    return render_template('layouts/vertical/layouts-preloader.html')   

@layouts.route('/layouts/vertical/colored_sidebar')
@login_required
def layouts_vertical_colored_sidebar():
    return render_template('layouts/vertical/layouts-colored-sidebar.html') 

@layouts.route('/layouts/vertical/scrollable_sidebar')
@login_required
def layouts_vertical_scrollable_sidebar():
    return render_template('layouts/vertical/layouts-scrollable-sidebar.html')     

#Horizontal layout    
@layouts.route('/layouts/horizontal/horizontal')
@login_required
def layouts_vertical_horizontal():
    return render_template('layouts/horizontal/layouts-horizontal.html') 

@layouts.route('/layouts/horizontal/hori-topbar-light')
@login_required
def layouts_hori_topbar_light():
    return render_template('layouts/horizontal/layouts-hori-topbar-light.html')     

@layouts.route('/layouts/horizontal/hori-boxed-width')
@login_required
def layouts_hori_boxed_width():
    return render_template('layouts/horizontal/layouts-hori-boxed-width.html')   

@layouts.route('/layouts/horizontal/hori-preloader')
@login_required
def layouts_hori_preloader():
    return render_template('layouts/horizontal/layouts-hori-preloader.html')      

@layouts.route('/layouts/horizontal/hori-colored-header')
@login_required
def layouts_hori_colored_header():
    return render_template('layouts/horizontal/layouts-hori-colored-header.html')   

@layouts.route('/layouts/horizontal/hori-scrollable')
@login_required
def layouts_hori_scrollable():
    return render_template('layouts/horizontal/layouts-hori-scrollable.html')        


