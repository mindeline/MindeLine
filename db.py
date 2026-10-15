from datetime import datetime

_ALERTAS = []


def init_db():
    # Versión sin base de datos: el almacenamiento es en memoria para demo/validación.
    return None


def guardar_alerta(nombre_paciente, tipo_mensaje, contenido, transcripcion, nivel, resumen, phq9):
    alerta_id = len(_ALERTAS) + 1
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _ALERTAS.insert(0, {
        'id': alerta_id,
        'nombre_paciente': nombre_paciente,
        'fecha': fecha,
        'tipo_mensaje': tipo_mensaje,
        'transcripcion': transcripcion,
        'nivel_riesgo': nivel,
        'resumen_clinico': resumen,
        'phq9': phq9,
        'estado': 'Pendiente',
    })
    return alerta_id


def obtener_alertas():
    filas = []
    for item in _ALERTAS:
        filas.append((
            item['id'],
            item['nombre_paciente'],
            item['fecha'],
            item['tipo_mensaje'],
            item['transcripcion'],
            item['nivel_riesgo'],
            item['resumen_clinico'],
            item['phq9'],
            item['estado'],
        ))
    return filas


def actualizar_estado_alerta(alerta_id, nuevo_estado):
    for item in _ALERTAS:
        if item['id'] == alerta_id:
            item['estado'] = nuevo_estado
            break
    return True