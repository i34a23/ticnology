from flask import Blueprint,render_template
from flask_login import login_required

components = Blueprint('components',__name__,template_folder='templates',
    static_folder='static',)

@components.route('/components/ui/alerts')
@login_required
def ui_alerts():
    return render_template('components/ui/ui-alerts.html')

@components.route('/components/ui/buttons')
@login_required
def ui_buttons():
    return render_template('components/ui/ui-buttons.html')    

@components.route('/components/ui/cards')
@login_required
def ui_cards():
    return render_template('components/ui/ui-cards.html')    

@components.route('/components/ui/carousel')
@login_required
def ui_carousel():
    return render_template('components/ui/ui-carousel.html')     

@components.route('/components/ui/dropdowns')
@login_required
def ui_dropdowns():
    return render_template('components/ui/ui-dropdowns.html')    

@components.route('/components/ui/grid')
@login_required
def ui_grid():
    return render_template('components/ui/ui-grid.html')       

@components.route('/components/ui/images')
@login_required
def ui_images():
    return render_template('components/ui/ui-images.html')  

@components.route('/components/ui/lightbox')
@login_required
def ui_lightbox():
    return render_template('components/ui/ui-lightbox.html')         

@components.route('/components/ui/modals')
@login_required
def ui_modals():
    return render_template('components/ui/ui-modals.html')      

@components.route('/components/ui/offcanvas')
@login_required
def ui_offcanvas():
    return render_template('components/ui/ui-offcanvas.html')

@components.route('/components/ui/rangeslider')
@login_required
def ui_rangeslider():
    return render_template('components/ui/ui-rangeslider.html')      

@components.route('/components/ui/session-timeout')
@login_required
def ui_session_timeout():
    return render_template('components/ui/ui-session-timeout.html')    

@components.route('/components/ui/progressbars')
@login_required
def ui_progressbars():
    return render_template('components/ui/ui-progressbars.html')   

@components.route('/components/ui/placeholders')
@login_required
def ui_placeholders():
    return render_template('components/ui/ui-placeholders.html')    

@components.route('/components/ui/sweet-alert')
@login_required
def ui_sweet_alert():
    return render_template('components/ui/ui-sweet-alert.html')    

@components.route('/components/ui/tabs-accordions')
@login_required
def ui_tabs_accordions():
    return render_template('components/ui/ui-tabs-accordions.html')      

@components.route('/components/ui/typography')
@login_required
def ui_typography():
    return render_template('components/ui/ui-typography.html')   

@components.route('/components/ui/toasts')
@login_required
def ui_toasts():
    return render_template('components/ui/ui-toasts.html')    

@components.route('/components/ui/video')
@login_required
def ui_video():
    return render_template('components/ui/ui-video.html') 

@components.route('/components/ui/general')
@login_required
def ui_general():
    return render_template('components/ui/ui-general.html')                 

@components.route('/components/ui/colors')
@login_required
def ui_colors():
    return render_template('components/ui/ui-colors.html')

@components.route('/components/ui/rating')
@login_required
def ui_rating():
    return render_template('components/ui/ui-rating.html')    

@components.route('/components/ui/notifications')
@login_required
def ui_notifications():
    return render_template('components/ui/ui-notifications.html')

@components.route('/components/ui/utilities')
@login_required
def ui_utilities():
    return render_template('components/ui/ui-utilities.html')  

#forms pages      
@components.route('/components/forms/forms-elements')
@login_required
def forms_elements():
    return render_template('components/forms/forms-elements.html') 

@components.route('/components/forms/forms-layouts')
@login_required
def forms_layouts():
    return render_template('components/forms/forms-layouts.html')    

@components.route('/components/forms/forms-validation')
@login_required
def forms_validation():
    return render_template('components/forms/forms-validation.html')  

@components.route('/components/forms/forms-advanced')
@login_required
def forms_advanced():
    return render_template('components/forms/forms-advanced.html')    

@components.route('/components/forms/forms-editors')
@login_required
def forms_editors():
    return render_template('components/forms/forms-editors.html')       

@components.route('/components/forms/forms-uploads')
@login_required
def forms_uploads():
    return render_template('components/forms/forms-uploads.html')  

@components.route('/components/forms/forms-xeditable')
@login_required
def forms_xeditable():
    return render_template('components/forms/forms-xeditable.html')       

@components.route('/components/forms/forms-repeater')
@login_required
def forms_repeater():
    return render_template('components/forms/forms-repeater.html')   

@components.route('/components/forms/forms-wizard')
@login_required
def forms_wizard():
    return render_template('components/forms/forms-wizard.html')   

@components.route('/components/forms/forms-mask')
@login_required
def forms_mask():
    return render_template('components/forms/forms-mask.html') 

#Tables pages          
@components.route('/components/tables/tables-basic')
@login_required
def tables_basic():
    return render_template('components/tables/tables-basic.html') 

@components.route('/components/tables/tables-datatable')
@login_required
def tables_datatable():
    return render_template('components/tables/tables-datatable.html')     

@components.route('/components/tables/tables-responsive')
@login_required
def tables_responsive():
    return render_template('components/tables/tables-responsive.html')     

@components.route('/components/tables/tables-editable')
@login_required
def tables_editable():
    return render_template('components/tables/tables-editable.html')  

#Charts Pages 
@components.route('/components/charts/charts-apex')
@login_required
def charts_apex():
    return render_template('components/charts/charts-apex.html') 

@components.route('/components/charts/charts-echart')
@login_required
def charts_echart():
    return render_template('components/charts/charts-echart.html')    

@components.route('/components/charts/charts-chartjs')
@login_required
def charts_chartjs():
    return render_template('components/charts/charts-chartjs.html')

@components.route('/components/charts/charts-flot')
@login_required
def charts_flot():
    return render_template('components/charts/charts-flot.html') 

@components.route('/components/charts/charts-tui')
@login_required
def charts_tui():
    return render_template('components/charts/charts-tui.html')        

@components.route('/components/charts/charts-knob')
@login_required
def charts_knob():
    return render_template('components/charts/charts-knob.html')  

@components.route('/components/charts/charts-sparkline')
@login_required
def charts_sparkline():
    return render_template('components/charts/charts-sparkline.html')   

#Icons Page
@components.route('/components/icons/icons-boxicons')
@login_required
def icons_boxicons():
    return render_template('components/icons/icons-boxicons.html')          

@components.route('/components/icons/icons-materialdesign')
@login_required
def icons_materialdesign():
    return render_template('components/icons/icons-materialdesign.html')   

@components.route('/components/icons/icons-dripicons')
@login_required
def icons_dripicons():
    return render_template('components/icons/icons-dripicons.html')     

@components.route('/components/icons/icons-fontawesome')
@login_required
def icons_fontawesome():
    return render_template('components/icons/icons-fontawesome.html')

#Maps Pages

@components.route('/components/maps/maps-google')
@login_required
def maps_google():
    return render_template('components/maps/maps-google.html')

@components.route('/components/maps/maps-vector')
@login_required
def maps_vector():
    return render_template('components/maps/maps-vector.html')    

@components.route('/components/maps/maps-leaflet')
@login_required
def maps_leaflet():
    return render_template('components/maps/maps-leaflet.html')        