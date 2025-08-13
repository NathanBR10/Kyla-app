import streamlit as st
import pandas as pd
import os
from PIL import Image
import difflib
import datetime

# ======================
# CONFIGURACIÓN INICIAL
# ======================
st.set_page_config(page_title="Kyla", layout="wide")
st.markdown("<h1 style='text-align: center; color: #4A90E2;'>🏡 Kyla</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Encuentra o publica tu próximo hogar</p>", unsafe_allow_html=True)

# ======================
# FUNCIONES DE UTILIDAD
# ======================
def normalize_text(text):
    text = str(text).lower().strip()
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text

def is_match(query, text, threshold=0.4):
    if not query or not text:
        return False
    q = normalize_text(query)
    t = normalize_text(text)
    if q in t:
        return True
    score = difflib.SequenceMatcher(None, q, t).ratio()
    return score >= threshold

# ======================
# CARGA DE DATOS
# ======================
@st.cache_data
def load_data():
    try:
        properties = pd.read_csv("data/properties.csv", encoding="utf-8")
        users = pd.read_csv("data/users.csv", encoding="utf-8")

        # Validar que no estén vacíos
        if properties.empty:
            st.error("❌ El archivo 'properties.csv' está vacío.")
            st.stop()

        if users.empty:
            st.error("❌ El archivo 'users.csv' está vacío.")
            st.stop()

        # Asegurar que el precio sea numérico
        properties["price"] = pd.to_numeric(properties["price"], errors="coerce")
        properties = properties.dropna(subset=["price"])
        properties["price"] = properties["price"].astype(int)

        # Asegurar que las columnas de texto sean strings
        for col in ["title", "location", "description", "amenities"]:
            if col in properties.columns:
                properties[col] = properties[col].astype(str).fillna("")

        # Asegurar que el email y contraseña sean string
        users["email"] = users["email"].astype(str).fillna("")
        users["password"] = users["password"].astype(str)

        return properties, users

    except FileNotFoundError as e:
        st.error("❌ No se encontraron los archivos de datos. Verifica que están en GitHub.")
        st.stop()
    except Exception as e:
        st.error("❌ Error al cargar los datos. Verifica el formato de los CSV.")
        st.stop()

# Cargar datos y guardar en session_state
if "properties_df" not in st.session_state or "users_df" not in st.session_state:
    st.session_state.properties_df, st.session_state.users_df = load_data()

# ======================
# ESTADO DE SESIÓN
# ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "selected_property" not in st.session_state:
    st.session_state.selected_property = None
if "applications" not in st.session_state:
    st.session_state.applications = []


# ======================
# FUNCIONES AUXILIARES
# ======================
def get_user(email):
    if not email or email.strip() == "":
        return None

    # Normalizar email: minúsculas y sin espacios
    normalized_email = email.strip().lower()

    # Buscar en el DataFrame (también en minúsculas)
    user = users_df[users_df["email"].str.lower() == normalized_email]

    if not user.empty:
        return user.iloc[0]
    return None


# ======================
# PÁGINAS DE LA APP
# ======================
def show_auth():
    st.subheader("🔐 Bienvenido a Kyla")
    tab1, tab2 = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        if st.button("Entrar", key="login_btn"):
            email = email.strip().lower()  # Normalizar a minúsculas
            password = password.strip()

            user = get_user(email)
            if user is not None and str(user["password"]) == password:
                st.session_state.logged_in = True
                st.session_state.user_email = email  # Guardar en minúsculas
                st.session_state.current_page = "home"
                st.success(f"¡Hola de nuevo, {user['name']}!")
                st.rerun()
            else:
                st.error("Email o contraseña incorrectos")

    with tab2:
        name = st.text_input("Nombre completo")
        email = st.text_input("Email")
        phone = st.text_input("Teléfono")
        password = st.text_input("Contraseña", type="password")
        is_owner = st.checkbox("¿Quieres publicar inmuebles?")

        if st.button("Registrarse"):
            email = email.strip().lower()  # Normalizar a minúsculas

            # Acceder a los DataFrames desde session_state
            properties_df = st.session_state.properties_df
            users_df = st.session_state.users_df

            if get_user(email):
                st.error("Este email ya está registrado.")
            else:
                new_user = pd.DataFrame([{
                    "id": len(users_df) + 1,
                    "name": name,
                    "email": email,  # Guardar en minúsculas
                    "password": password,
                    "phone": phone,
                    "rating_count": 0,
                    "rating_avg": 0,
                    "is_owner": int(is_owner)
                }])

                # Guardar en CSV
                new_user.to_csv("data/users.csv", mode="a", header=False, index=False)

                # Recargar los datos
                st.cache_data.clear()
                st.session_state.properties_df, st.session_state.users_df = load_data()

                st.success("✅ ¡Cuenta creada! Ya puedes iniciar sesión.")
                st.balloons()


def show_home():
    st.markdown("### 🏠 Encuentra tu próximo hogar")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Buscar por ubicación, nombre o características")
    with col2:
        min_price = st.number_input("Precio mínimo", 0, 10000000, 0)
    with col3:
        max_price = st.number_input("Precio máximo", 0, 10000000, 2000000)

    # Aplicar filtros
    filtered = properties_df.copy()

    # Búsqueda inteligente
    if search:
        filtered = filtered[
            filtered.apply(
                lambda row: is_match(search, row["title"]) or is_match(search, row["location"]),
                axis=1
            )
        ]

    # Filtro de precio
    filtered = filtered[(filtered["price"] >= min_price) & (filtered["price"] <= max_price)]

    # Mostrar resultados
    if filtered.empty:
        st.info("📭 No se encontraron propiedades con esos filtros.")
    else:
        for _, prop in filtered.iterrows():
            owner = users_df[users_df["id"] == prop["owner_id"]].iloc[0]
            with st.container():
                cols = st.columns([1, 3, 1])
                with cols[0]:
                    img_path = f"assets/images/{prop['images'].split(',')[0]}"
                    if os.path.exists(img_path):
                        image = Image.open(img_path)
                        st.image(image, width=120)
                with cols[1]:
                    st.markdown(f"**{prop['title']}**")
                    st.markdown(f"📍 {prop['location']} | 💰 ${prop['price']:,} COP")
                    st.markdown(f"🛏️ {prop['beds']} | 🛁 {prop['baths']} | 📏 {prop['area']} m² | ⭐ {prop['rating']}")
                    st.markdown(f"🏠 Arrendador: {owner['name']} (⭐ {owner['rating_avg']})")
                with cols[2]:
                    if st.button("Ver", key=f"view_{prop['id']}"):
                        st.session_state.selected_property = prop["id"]
                        st.session_state.current_page = "property_detail"
                        st.rerun()  # ¡CRÍTICO!
                st.markdown("---")


def show_property_detail():
    prop_id = st.session_state.selected_property
    if not prop_id:
        st.error("No se seleccionó ninguna propiedad.")
        if st.button("Volver al inicio"):
            st.session_state.current_page = "home"
            st.rerun()
        return

    # Buscar propiedad
    prop = properties_df[properties_df["id"] == prop_id]
    if prop.empty:
        st.error("❌ Propiedad no encontrada.")
        if st.button("Volver al inicio"):
            st.session_state.current_page = "home"
            st.session_state.selected_property = None
            st.rerun()
        return

    prop = prop.iloc[0]
    owner = users_df[users_df["id"] == prop["owner_id"]].iloc[0]

    # Mostrar imágenes
    valid_images = []
    for img in prop["images"].split(","):
        img_path = f"assets/images/{img.strip()}"
        if os.path.exists(img_path):
            valid_images.append(img_path)

    if valid_images:
        st.image(valid_images, width=300)
    else:
        st.image("https://via.placeholder.com/300x200?text=Sin+imagen", width=300)

    # Detalles de la propiedad
    st.title(prop["title"])
    st.subheader(f"📍 {prop['location']}")
    st.markdown(f"**Precio:** ${prop['price']:,} COP/mes")
    st.markdown(f"**Características:** {prop['beds']} hab, {prop['baths']} baños, {prop['area']} m²")
    st.write(prop["description"])
    st.markdown(f"**Servicios:** {prop['amenities'].replace(',', ', ')}")

    st.markdown("---")
    st.subheader("👤 Arrendador")
    st.markdown(f"**Nombre:** {owner['name']}")
    st.markdown(f"**Teléfono:** {owner['phone']}")
    st.markdown(f"**Reputación:** ⭐ {owner['rating_avg']} ({owner['rating_count']} reseñas)")

    # Botones de acción
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📩 Contactar arrendador", use_container_width=True):
            st.success("Mensaje enviado. ¡El arrendador se pondrá en contacto contigo!")

    with col2:
        if st.button("📩 Iniciar proceso de arrendamiento", type="primary", use_container_width=True):
            st.session_state.current_page = "rental_application"
            st.rerun()  # ¡ESTO ES LO QUE FALTABA!

    if st.button("⬅️ Volver al inicio", use_container_width=True):
        st.session_state.current_page = "home"
        st.session_state.selected_property = None
        st.rerun()


def show_rental_application():
    prop_id = st.session_state.selected_property
    if not prop_id:
        st.error("No hay propiedad seleccionada.")
        if st.button("Volver al inicio"):
            st.session_state.current_page = "home"
            st.rerun()
        return

    # Buscar propiedad
    prop = properties_df[properties_df["id"] == prop_id]
    if prop.empty:
        st.error("Propiedad no encontrada.")
        return
    prop = prop.iloc[0]

    user = get_user(st.session_state.user_email)
    if user is None:  # ✅ CORREGIDO
        st.error("Usuario no autenticado.")
        return

    # Encabezado
    st.markdown("<h2 style='color: #4A90E2;'>📝 Solicitud de Arrendamiento</h2>", unsafe_allow_html=True)
    st.markdown(f"**Vivienda:** {prop['title']} en {prop['location']}")

    # Documentos requeridos
    st.markdown("### 📄 Documentos requeridos")
    st.info("""
    - Copia del documento de identidad  
    - Comprobante de ingresos  
    - Referencias personales  
    - Historial crediticio (opcional)  
    """)

    # Comentarios
    st.markdown("### 💬 Comentarios al arrendador")
    comments = st.text_area("Escribe un mensaje", height=100)

    # Subir documentos
    st.markdown("### 📎 Adjuntar documentos")
    uploaded_files = st.file_uploader(
        "Sube tus documentos (PDF, JPG, PNG)",
        accept_multiple_files=True,
        type=["pdf", "jpg", "png", "docx"]
    )

    # Botón de enviar
    if st.button("📤 Enviar solicitud", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Por favor, adjunta al menos un documento.")
        else:
            # Crear nueva solicitud
            new_app = {
                "property_id": prop["id"],
                "property_title": prop["title"],
                "applicant_name": user["name"],
                "applicant_email": user["email"],
                "comments": comments,
                "files": [f.name for f in uploaded_files],
                "status": "En revisión",
                "timestamp": datetime.datetime.now()
            }

            # Guardar en sesión
            st.session_state.applications.append(new_app)

            # Confirmación
            st.success("✅ ¡Solicitud enviada con éxito!")
            st.info("El arrendador la revisará pronto. Puedes ver el estado en tu perfil.")
            st.balloons()

            # Volver al inicio después de 2 segundos
            if st.button("Volver al inicio", use_container_width=True):
                st.session_state.current_page = "home"
                st.rerun()

    # Botón de volver
    if st.button("⬅️ Volver", use_container_width=True):
        st.session_state.current_page = "property_detail"
        st.rerun()


def show_profile():
    user = get_user(st.session_state.user_email)
    if user is not None:
        st.error("❌ Sesión inválida. Por favor, inicia sesión nuevamente.")
        st.session_state.logged_in = False
        if st.button("Volver al inicio"):
            st.rerun()
        return

    st.subheader(f"👤 Mi perfil: {user['name']}")
    st.markdown(f"**Email:** {user['email']}")
    st.markdown(f"**Teléfono:** {user['phone']}")
    st.markdown(f"**Tipo:** {'Arrendador' if user['is_owner'] else 'Arrendatario'}")
    st.markdown(f"**Calificación:** ⭐ {user['rating_avg']} ({user['rating_count']} reseñas)")

    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.current_page = "home"
        st.rerun()

    # Buzón de solicitudes (solo para arrendadores)
    if user["is_owner"]:
        st.markdown("---")
        st.subheader("📬 Buzón de solicitudes de arrendamiento")

        owner_apps = []
        for app in st.session_state.applications:
            prop = properties_df[properties_df["id"] == app["property_id"]]
            if not prop.empty and prop.iloc[0]["owner_id"] == user["id"]:
                owner_apps.append(app)

        if not owner_apps:
            st.info("📭 No tienes solicitudes pendientes.")
        else:
            for i, app in enumerate(owner_apps):
                with st.expander(f"📄 {app['applicant_name']} - {app['property_title']}"):
                    st.write(f"**Email:** {app['applicant_email']}")
                    st.write(f"**Comentarios:** {app['comments']}")
                    st.write(f"**Archivos adjuntos:** {', '.join(app['files'])}")
                    st.write(f"**Fecha:** {app['timestamp'].strftime('%d/%m/%Y %H:%M')}")
                    st.write(f"**Estado:** {app['status']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Aprobar", key=f"approve_{i}", use_container_width=True):
                            app["status"] = "Aprobada"
                            st.success("✅ Solicitud aprobada")
                            st.rerun()

                    with col2:
                        if st.button("Rechazar", key=f"reject_{i}", use_container_width=True):
                            app["status"] = "Rechazada"
                            st.warning("🚫 Solicitud rechazada")
                            st.rerun()


# ======================
# FLUJO PRINCIPAL (CRÍTICO)
# ======================
def main():
    # Mostrar estado para diagnóstico (opcional)
    if st.session_state.debug_mode:
        with st.expander("🔧 Estado de sesión (debug)"):
            st.write("current_page:", st.session_state.current_page)
            st.write("logged_in:", st.session_state.logged_in)
            st.write("selected_property:", st.session_state.selected_property)
            st.write("applications:", len(st.session_state.applications), "solicitudes")

    # Flujo principal
    if not st.session_state.logged_in:
        show_auth()
    else:
        # Verificar que el usuario exista
        user = get_user(st.session_state.user_email)
        if user is None:
            # Usuario no existe - limpiar sesión
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.error("❌ Sesión inválida. Por favor, inicia sesión nuevamente.")
            st.rerun()
            return
        # Barra lateral
        with st.sidebar:
            st.title("Kyla")
            st.markdown(f"👤 {user['name']}")

            # Navegación
            page = st.radio("Ir a", ["Inicio", "Mi perfil"])

            if page == "Inicio":
                st.session_state.current_page = "home"
            elif page == "Mi perfil":
                st.session_state.current_page = "profile"

        # Renderizar página actual
        if st.session_state.current_page == "home":
            show_home()
        elif st.session_state.current_page == "property_detail":
            show_property_detail()
        elif st.session_state.current_page == "rental_application":
            show_rental_application()
        elif st.session_state.current_page == "profile":
            show_profile()


if __name__ == "__main__":
    main()