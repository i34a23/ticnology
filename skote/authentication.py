from flask import Blueprint,render_template,request,redirect,url_for,flash
from flask_login import login_user,logout_user,login_required
from pyrfc3339 import generate
from .models import User
from werkzeug.security import generate_password_hash,check_password_hash
from . import db
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy import or_
from flask_wtf.csrf import validate_csrf

authentication = Blueprint('authentication',__name__,template_folder='templates',
    static_folder='static',)

@authentication.route('/authentication/login/')
@login_required
def auth_login():
    return render_template('authentication/auth-login.html')

@authentication.route('/authentication/login2/')
@login_required
def auth_login2():
    return render_template('authentication/auth-login-2.html')    

@authentication.route('/authentication/register/')
@login_required
def auth_register():
    return render_template('authentication/auth-register.html')       

@authentication.route('/authentication/register2/')
@login_required
def auth_register2():
    return render_template('authentication/auth-register-2.html')        

@authentication.route('/authentication/recoverpw/')
@login_required
def auth_recoverpw():
    return render_template('authentication/auth-recoverpw.html')   

@authentication.route('/authentication/recoverpw2/')
@login_required
def auth_recoverpw2():
    return render_template('authentication/auth-recoverpw-2.html')    

@authentication.route('/authentication/lockscreen/')
@login_required
def auth_lockscreen():
    return render_template('authentication/auth-lock-screen.html')       

@authentication.route('/authentication/lockscreen2/')
@login_required
def auth_lockscreen2():
    return render_template('authentication/auth-lock-screen-2.html')

@authentication.route('/authentication/confirm-mail/')
@login_required
def auth_confirm_mail():
    return render_template('authentication/auth-confirm-mail.html') 

@authentication.route('/authentication/confirm-mail-2/')
@login_required
def auth_confirm_mail2():
    return render_template('authentication/auth-confirm-mail-2.html')              

@authentication.route('/authentication/email-verification/')
@login_required
def auth_email_verification():
    return render_template('authentication/auth-email-verification.html') 

@authentication.route('/authentication/email-verification-2/')
@login_required
def auth_email_verification2():
    return render_template('authentication/auth-email-verification-2.html')         

@authentication.route('/authentication/two-step-verification/')
@login_required
def auth_two_step_verification():
    return render_template('authentication/auth-two-step-verification.html')       

@authentication.route('/authentication/two-step-verification-2/')
@login_required
def auth_two_step_verification2():
    return render_template('authentication/auth-two-step-verification-2.html')     

@authentication.route('/account/login')  
def login():
    return render_template('account/login.html')   

@authentication.route('/account/login',methods=['POST'])  
def login_post():
    if request.method == 'POST':
        try:
            # 1. Obtiene el token CSRF del formulario
            csrf_token = request.form.get('csrf_token')
            
            # 2. Valida el token
            validate_csrf(csrf_token)
        except Exception as e:
            # Manejo del error si la validación falla
            flash("Error de seguridad: token CSRF no válido.")
            print(f"CSRF validation failed: {e}")  # Opcional, para depuración
            return redirect(url_for('authentication.login'))
            
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Credenciales inválidas")
            return redirect(url_for('authentication.login'))

        login_user(user, remember=remember)
        
        return redirect(url_for('dashboards.index'))

@authentication.route('/account/signup')  
def signup(): 
    return render_template('account/signup.html')    

@authentication.route('/account/signup',methods=['POST'])  
def signup_post():
    # 1) Normalización
    email = (request.form.get('email') or "").strip().lower()
    username = (request.form.get('username') or "").strip()
    password = request.form.get('password') or ""

    # 2) Validaciones mínimas (ajusta a tus reglas)
    if not email or not username or not password:
        flash("Email, username y password son obligatorios.")
        return redirect(url_for('authentication.signup'))
    if len(username) < 3:
        flash("El username debe tener al menos 3 caracteres.")
        return redirect(url_for('authentication.signup'))
    if len(password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.")
        return redirect(url_for('authentication.signup'))

    # 3) Comprobación previa (opcional; el control real lo hace la BD)
    existing = User.query.filter(or_(User.email == email, User.username == username)).first()
    if existing:
        if existing.email == email:
            flash("User email already exists")
        else:
            flash("Username already exists")
        return redirect(url_for('authentication.signup'))

    # 4) Alta con hash robusto
    new_user = User(
        email=email,
        username=username,
        password=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
    )

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Si hubo condición de carrera, damos feedback correcto
        flash("Email o username ya existen.")
        return redirect(url_for('authentication.signup'))
    except DataError:
        db.session.rollback()
        flash("Datos demasiado largos o con formato inválido.")
        return redirect(url_for('authentication.signup'))

    flash("Successfully signup")
    return redirect(url_for('authentication.login'))
    
@authentication.route('/account/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('authentication.login'))    