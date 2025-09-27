from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional


class CreateJourneyForm(FlaskForm):
    """Formulario para crear o editar un Lead Journey."""
    nombre = StringField(
        'Nombre del Journey',
        validators=[DataRequired(), Length(min=2, max=255)]
    )
    descripcion = TextAreaField('Descripción (opcional)')
    submit = SubmitField('Guardar Journey')


class BranchForm(FlaskForm):
    """Subformulario para definir un branch (NextStep)."""
    etiqueta = StringField('Etiqueta', validators=[DataRequired()])
    condicion_logica = StringField('Condición lógica', validators=[Optional()])
    nodo_destino_id = StringField('Nodo destino', validators=[Optional()])


class NodeForm(FlaskForm):
    """Formulario para crear o editar un nodo."""
    nombre = StringField('Nombre del Nodo', validators=[DataRequired()])
    prompt_agent = TextAreaField('Prompt para el Agente', validators=[DataRequired()])
    completion_condition = StringField(
        'Condición de Cumplimiento',
        validators=[Optional()],
        description="Ej: documento_subido == true"
    )

    # Lista de branches opcionales (solo para nodos padres)
    next_steps = FieldList(FormField(BranchForm), min_entries=0)

    submit = SubmitField('Guardar Nodo')
