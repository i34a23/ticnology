from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional
from .models import EstadoUsuarioEnum

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre del cliente', validators=[
        DataRequired(),
        Length(min=2, max=255)
    ])
    submit = SubmitField('Guardar')

class UsuarioForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired()])
    apellido = StringField("Apellido", validators=[DataRequired()])
    estado = SelectField("Estado", choices=[(e.name, e.name) for e in EstadoUsuarioEnum])
    extra_json = TextAreaField("Datos adicionales (JSON)")  # No corresponde al modelo
    submit = SubmitField("Guardar")