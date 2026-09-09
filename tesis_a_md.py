import psycopg2
import os

# Configuración de tu laboratorio local
DB_CONFIG = {
    "dbname": "practica_legal",
    "user": "postgres",
    "password": "6419",
    "host": "localhost"
}

def exportar_a_markdown(registro_digital):
    try:
        # 1. Conexión al motor local
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. Consulta de precisión
        query = "SELECT * FROM jurisprudencias WHERE registro_digital = %s;"
        cur.execute(query, (registro_digital,))
        columna_nombres = [desc[0] for desc in cur.description]
        fila = cur.fetchone()

        if not fila:
            print(f"❌ No encontré la tesis con registro: {registro_digital}")
            return

        # Convertimos la fila en un diccionario para fácil acceso
        tesis = dict(zip(columna_nombres, fila))

        # 3. Construcción del contenido Markdown
        md_content = f"""# ⚖️ Tesis: {tesis['registro_digital']}
        
## 📌 TEMA / RUBRO
**{tesis['rubro']}**

---

### 🏛️ DATOS DE IDENTIFICACIÓN
*   **Instancia:** {tesis['instancia']}
*   **Época:** {tesis['epoca']}
*   **Materia:** {tesis['materia']}
*   **Expediente:** {tesis['expediente']}
*   **Publicación:** {tesis['fecha_publicacion']}

---

### 📝 RESUMEN (IA)
{tesis['resumen_ia'] if tesis['resumen_ia'] else "Sin resumen disponible."}

---

### 📖 CUERPO DE LA TESIS
#### **Hechos:**
{tesis['hechos']}

#### **Criterio Jurídico:**
{tesis['criterio_juridico']}

#### **Justificación:**
{tesis['justificacion']}

---
*Generado desde el Laboratorio LegalTech NV59*
"""

        # 4. Guardar el archivo
        nombre_archivo = f"tesis_{registro_digital}.md"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"✅ ¡Listo, Tocayo! Archivo creado: {nombre_archivo}")
        print(f"📂 Puedes abrirlo en VS Code para verlo con formato profesional.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

if __name__ == "__main__":
    registro = input("Introduce el Registro Digital que quieres extraer: ")
    exportar_a_markdown(registro)
