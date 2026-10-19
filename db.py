import sqlite3

def init_db():
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_paciente TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo_mensaje TEXT,
            transcripcion TEXT,
            nivel_riesgo TEXT,
            resumen_clinico TEXT,
            phq9 INTEGER,
            estado TEXT DEFAULT 'Pendiente'
        )
    ''')
    conn.commit()
    conn.close()

def guardar_alerta(nombre_paciente, tipo_mensaje, contenido, transcripcion, nivel, resumen, phq9):
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO alertas (nombre_paciente, tipo_mensaje, transcripcion, nivel_riesgo, resumen_clinico, phq9)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nombre_paciente, tipo_mensaje, transcripcion, nivel, resumen, phq9))
    conn.commit()
    conn.close()

def obtener_alertas():
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    c.execute('SELECT id, nombre_paciente, fecha, tipo_mensaje, transcripcion, nivel_riesgo, resumen_clinico, phq9, estado FROM alertas ORDER BY id DESC')
    filas = c.fetchall()
    conn.close()
    return filas

def actualizar_estado_alerta(alerta_id, nuevo_estado):
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    c.execute('UPDATE alertas SET estado = ? WHERE id = ?', (nuevo_estado, alerta_id))
    conn.commit()
    conn.close()

def reiniciar_base_datos():
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    c.execute('DELETE FROM alertas')
    conn.commit()
    conn.close()

def sembrar_datos_prueba():
    casos = [
        ("María González", "Texto", "Siento un vacio enorme, ya no quiero despertar mañana y tengo las pastillas en la mesa", "Nivel A: Riesgo vital activo con ideación suicida e ingesta potencial.", "A", 24),
        ("Carlos Muñoz", "Audio", "Llevo tres días sin dormir nada, siento que me persiguen y tengo mucha angustia", "Nivel B: Episodio de agitación psíquica e insomnio severo.", "B", 18),
        ("Ana Silva", "Texto", "El medicamento nuevo me está dando mucho dolor de cabeza y desánimo elevadisimo", "Nivel C: Síntomas adversos con desánimo elevado. Ajuste sugerido en 72h.", "C", 12),
        ("Pedro Morales", "Texto", "Hola doctor, quería confirmar si me mantengo con la misma dosis de sertralina", "Nivel E: Reporte habitual y consulta de control rutinaria.", "E", 4),
    ]
    conn = sqlite3.connect('mindeline.db')
    c = conn.cursor()
    for nombre, tipo, trans, res, nivel, phq in casos:
        c.execute('''
            INSERT INTO alertas (nombre_paciente, tipo_mensaje, transcripcion, nivel_riesgo, resumen_clinico, phq9)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, tipo, trans, nivel, res, phq))
    conn.commit()
    conn.close()