from flask import Blueprint,render_template
from flask_login import login_required

ecommerce = Blueprint('ecommerce',__name__,template_folder='templates',
    static_folder='static',)

@ecommerce.route('/ecommerce/products/')
@login_required
def ecommerce_products():
    return render_template('ecommerce/ecommerce-products.html')

@ecommerce.route('/ecommerce/product-detail/')
@login_required
def ecommerce_product_detail():
    return render_template('ecommerce/ecommerce-product-detail.html')    

@ecommerce.route('/ecommerce/orders/')
@login_required
def ecommerce_orders():
    return render_template('ecommerce/ecommerce-orders.html')     

@ecommerce.route('/ecommerce/customers/')
@login_required
def ecommerce_customers():
    return render_template('ecommerce/ecommerce-customers.html')     

@ecommerce.route('/ecommerce/cart/')
@login_required
def ecommerce_cart():
    return render_template('ecommerce/ecommerce-cart.html')     

@ecommerce.route('/ecommerce/checkout/')
@login_required
def ecommerce_checkout():
    return render_template('ecommerce/ecommerce-checkout.html')  

@ecommerce.route('/ecommerce/shops/')
@login_required
def ecommerce_shops():
    return render_template('ecommerce/ecommerce-shops.html')    

@ecommerce.route('/ecommerce/add-product/')
@login_required
def ecommerce_add_product():
    return render_template('ecommerce/ecommerce-add-product.html')                