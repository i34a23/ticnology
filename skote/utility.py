from flask import Blueprint,render_template
# from flask_login import login_required

utility = Blueprint('utility',__name__,template_folder='templates',
    static_folder='static',)

@utility.route('/utility/starter/')
def utility_starter():
    return render_template('utility/pages-starter.html')

@utility.route('/utility/maintenance/')
def utility_maintenance():
    return render_template('utility/pages-maintenance.html')    

@utility.route('/utility/comingsoon/')
def utility_comingsoon():
    return render_template('utility/pages-comingsoon.html')   

@utility.route('/utility/timeline/')
def utility_timeline():
    return render_template('utility/pages-timeline.html')      

@utility.route('/utility/faqs/')
def utility_faqs():
    return render_template('utility/pages-faqs.html')     

@utility.route('/utility/pricing/')
def utility_pricing():
    return render_template('utility/pages-pricing.html')  

@utility.route('/utility/404error/')
def utility_404error():
    return render_template('utility/pages-404error.html')      
    
@utility.route('/utility/500error/')
def utility_500error():
    return render_template('utility/pages-500error.html')      