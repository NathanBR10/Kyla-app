import streamlit as st
import pandas as pd
import os
from PIL import Image
import difflib


# Configuración
st.set_page_config(page_title="Kyla", layout="wide")
st.markdown("<h1 style='text-align: center; color: #4A90E2;'>🏡 Kyla</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Encuentra o publica tu próximo hogar</p>",
            unsafe_allow_html=True)

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
    """
    Devuelve True si el texto es similar a la búsqueda
    threshold: 0.4 = flexible, 0.6 = estricto
    """
    if not query or not text:
        return False
    # Normalizar ambos textos
    q = normalize_text(query)
    t = normalize_text(text)
    # Buscar si la consulta está dentro del texto (flexible)
    if q in t:
        return True
    # O usar similitud de secuencia
    score = difflib.SequenceMatcher(None, q, t).ratio()
    return score >= threshold

# Cargar datos
@st.cache_data
def load_data():
    try:
        properties = pd.read_csv("data/properties.csv", encoding="utf-8")
        users = pd.read_csv("data/users.csv", encoding="utf-8")

        # ✅ Validar que no estén vacíos
        if properties.empty:
            st.error("❌ El archivo 'properties.csv' está vacío.")
            st.stop()

        if users.empty:
            st.error("❌ El archivo 'users.csv' está vacío.")
            st.stop()

        # 🔢 Asegurar que el precio sea numérico
        properties["price"] = pd.to_numeric(properties["price"], errors="coerce")
        # Eliminar filas con precio inválido
        properties = properties.dropna(subset=["price"])
        properties["price"] = properties["price"].astype(int)

        # 🔽 Aseguramos que las columnas de texto sean strings
        for col in ["title", "location", "description", "amenities"]:
            if col in properties.columns:
                properties[col] = properties[col].astype(str).fillna("")

        # Aseguramos que el email sea string
        users["email"] = users["email"].astype(str).fillna("")

        # Aseguramos que la contraseña sea string
        users["password"] = users["password"].astype(str)

        return properties, users

    except FileNotFoundError as e:
        st.error(
            "❌ No se encontraron los archivos de datos. Asegúrate de que `data/properties.csv` y `data/users.csv` están en GitHub.")
        st.code("Estructura esperada:\nkyla-app/\n├── data/\n│   ├── properties.csv\n│   └── users.csv")
        st.stop()

    except pd.errors.EmptyDataError:
        st.error("❌ Uno de los archivos CSV está vacío.")
        st.stop()

    except Exception as e:
        st.error("❌ Error al cargar los datos. Verifica que 'data/properties.csv' y 'data/users.csv' existan y tengan el formato correcto.")
        st.stop()


properties_df, users_df = load_data()

# Estado de sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""


def get_user(email):
    user = users_df[users_df["email"] == email]
    return user.iloc[0] if not user.empty else None


# Página de Login / Registro
def show_auth():
    st.subheader("🔐 Bienvenido a Kyla")
    tab1, tab2 = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        if st.button("Entrar", key="login_btn"):
            email = email.strip()  # Elimina espacios al inicio y final
            password = password.strip()
            user = get_user(email)
            if user is not None and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
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
            if get_user(email):
                st.error("Este email ya está registrado.")
            else:
                new_user = pd.DataFrame([{
                    "id": len(users_df) + 1,
                    "name": name,
                    "email": email,
                    "password": password,
                    "phone": phone,
                    "rating_count": 0,
                    "rating_avg": 0,
                    "is_owner": int(is_owner)
                }])
                new_user.to_csv("data/users.csv", mode="a", header=False, index=False)
                st.success("✅ ¡Cuenta creada! Ya puedes iniciar sesión.")
                st.balloons()


# Pantalla principal
def show_home():
    # 🔍 DEBUG: Verifica que hay datos
    st.write(f"📊 Total de propiedades cargadas: {len(properties_df)}")
    if len(properties_df) == 0:
        st.error("❌ No se cargaron propiedades. Revisa el archivo 'data/properties.csv'")
        return

    st.markdown("### 🏠 Encuentra tu próximo hogar")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Buscar por ubicación, nombre o características")
    with col2:
        min_price = st.number_input("Precio mínimo", 0, 10000000, 0)
    with col3:
        max_price = st.number_input("Precio máximo", 0, 10000000, 2000000)  # Sube el valor por defecto

    # Aplicar filtros
    filtered = properties_df.copy()

    # 🔎 Búsqueda inteligente en título y ubicación
    if search:
        query = search.lower().strip()
        # Normaliza tildes manualmente
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n'}
        for a, b in replacements.items():
            query = query.replace(a, b)
        filtered = filtered[
            filtered.apply(
                lambda row: is_match(search, row["title"]) or is_match(search, row["location"]),
                axis=1
            )
        ]

    # 💰 Filtro de precio
    filtered = filtered[(filtered["price"] >= min_price) & (filtered["price"] <= max_price)]

    # 📭 Mensaje si no hay resultados
    if filtered.empty:
        st.info("📭 No se encontraron propiedades con esos filtros. Intenta con otra búsqueda.")
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
                        st.rerun()
                st.markdown("---")


# Detalle de propiedad
def show_property_detail():
    prop_id = st.session_state.get("selected_property")

    if not prop_id:
        st.error("No se seleccionó ninguna propiedad.")
        if st.button("Volver al inicio"):
            st.rerun()
        return

    # Asegurarnos de que prop_id sea entero
    try:
        prop_id = int(prop_id)
    except (ValueError, TypeError):
        st.error("🆔 ID de propiedad inválido.")
        if st.button("Volver al inicio"):
            st.session_state.pop("selected_property", None)
            st.rerun()
        return

    # Buscar la propiedad
    prop_filtered = properties_df[properties_df["id"] == prop_id]
    if prop_filtered.empty:
        st.error("❌ No se encontró la propiedad solicitada.")
        if st.button("Volver al inicio"):
            if "selected_property" in st.session_state:
                del st.session_state.selected_property
            st.rerun()
        return

    prop = prop_filtered.iloc[0]  # Ahora seguro
    owner = users_df[users_df["id"] == prop["owner_id"]].iloc[0]

    # Lista para almacenar imágenes válidas
    valid_images = []

    for img in prop["images"].split(","):
        img = img.strip()
        img_path = f"assets/images/{img}"

        # Verifica si el archivo existe
        if os.path.exists(img_path):
            valid_images.append(img_path)
        else:
            st.warning(f"⚠️ Imagen no encontrada: {img_path}")

    # Muestra las imágenes o una por defecto
    if valid_images:
        st.image(valid_images, width=300, caption=[f"Imagen" for _ in valid_images])
    else:
        st.image("https://via.placeholder.com/300x200?text=Sin+imagen", width=300)
        st.write("No hay imágenes disponibles para esta propiedad.")
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

    if st.button("📩 Contactar arrendador"):
        st.success("Mensaje enviado. ¡El arrendador se pondrá en contacto contigo!")
    if st.button("📩 Iniciar proceso de arrendamiento", type="primary"):
        st.session_state.current_page = "rental_application"
        st.session_state.in_rental_process = True
        st.session_state.property_id = prop["id"]
        st.rerun()
    if st.button("⬅️ Volver al inicio"):
        del st.session_state.selected_property
        st.rerun()


# Publicar inmueble
def show_add_property():
    st.subheader("➕ Publica tu inmueble en Kyla")
    title = st.text_input("Título del inmueble")
    location = st.text_input("Ubicación")
    price = st.number_input("Precio mensual (COP)", min_value=100000, value=500000)
    beds = st.number_input("Habitaciones", 1, 5, 2)
    baths = st.number_input("Baños", 1, 4, 1)
    area = st.number_input("Área (m²)", 20, 300, 60)
    description = st.text_area("Descripción")
    amenities = st.multiselect(
        "Servicios",
        ["wifi", "parking", "pool", "gym", "elevator", "pet_friendly", "furnished"]
    )
    uploaded_files = st.file_uploader("Sube fotos", accept_multiple_files=True, type=["jpg", "png"])

    if st.button("Publicar ahora"):
        if not uploaded_files:
            st.error("Por favor, sube al menos una foto.")
        else:
            image_names = [f"img_{len(properties_df) + i + 1}.jpg" for i in range(len(uploaded_files))]
            for file, name in zip(uploaded_files, image_names):
                with open(f"assets/images/{name}", "wb") as f:
                    f.write(file.getvalue())

            new_prop = pd.DataFrame([{
                "id": len(properties_df) + 1,
                "title": title,
                "location": location,
                "price": price,
                "beds": beds,
                "baths": baths,
                "area": area,
                "description": description,
                "owner_id": get_user(st.session_state.user_email)["id"],
                "images": ",".join(image_names),
                "rating": 0,
                "amenities": ",".join(amenities)
            }])
            new_prop.to_csv("data/properties.csv", mode="a", header=False, index=False)
            st.success("🎉 ¡Tu inmueble ha sido publicado en Kyla!")
            st.balloons()

def show_profile():
    user = get_user(st.session_state.user_email)
    st.subheader(f"👤 Mi perfil: {user['name']}")

    user = get_user(st.session_state.user_email)
    st.subheader(f"👤 Mi perfil: {user['name']}")
    st.markdown(f"**Email:** {user['email']}")
    st.markdown(f"**Teléfono:** {user['phone']}")
    st.markdown(f"**Tipo:** {'Arrendador' if user['is_owner'] else 'Arrendatario'}")
    st.markdown(f"**Calificación:** ⭐ {user['rating_avg']} ({user['rating_count']} reseñas)")
    if st.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

    if user["is_owner"]:
        st.markdown("---")
        st.subheader("📬 Buzón de solicitudes de arrendamiento")

        # Filtrar solicitudes para propiedades de este owner
        if "applications" in st.session_state:
            owner_apps = []
            for app in st.session_state.applications:
                prop = properties_df[properties_df["title"] == app["property"]]
                if not prop.empty and prop.iloc[0]["owner_id"] == user["id"]:
                    owner_apps.append(app)

            if owner_apps:
                for i, app in enumerate(owner_apps):
                    with st.expander(f"📄 {app['applicant']} - {app['property']}"):
                        st.write(f"**Email:** {app['email']}")
                        st.write(f"**Comentarios:** {app['comments']}")
                        st.write(f"**Archivos adjuntos:** {', '.join(app['files'])}")
                        st.write(f"**Fecha:** {app['timestamp'].strftime('%d/%m/%Y %H:%M')}")
                        st.write(f"**Estado:** {app['status']}")

                        # Botón de aprobación
                        if st.button(f"Aprobar solicitud", key=f"approve_{i}"):
                            app["status"] = "Aprobada"
                            st.success(f"✅ Solicitud de {app['applicant']} aprobada")
                            st.rerun()

                        if st.button(f"Rechazar", key=f"reject_{i}"):
                            app["status"] = "Rechazada"
                            st.warning(f"🚫 Solicitud rechazada")
                            st.rerun()
            else:
                st.info("📭 No tienes solicitudes pendientes.")
        else:
            st.info("Aún no hay solicitudes.")

def show_rental_application():
    prop_id = st.session_state.get("property_id")
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
    owner = users_df[users_df["id"] == prop["owner_id"]].iloc[0]

    st.markdown("<h2 style='color: #4A90E2;'>📝 Solicitud de Arrendamiento</h2>", unsafe_allow_html=True)
    st.markdown(f"**Vivienda:** {prop['title']} en {prop['location']}")

    st.markdown("### 📄 Documentos requeridos")
    st.info("""
    - Copia del documento de identidad  
    - Comprobante de ingresos  
    - Referencias personales  
    - Historial crediticio (opcional)  
    """)

    st.markdown("### 💬 Comentarios al arrendador")
    comments = st.text_area("Escribe un mensaje", height=100)

    st.markdown("### 📎 Adjuntar documentos")
    uploaded_files = st.file_uploader(
        "Sube tus documentos (PDF, JPG, PNG)",
        accept_multiple_files=True,
        type=["pdf", "jpg", "png", "docx"]
    )

    if st.button("📤 Enviar solicitud", type="primary"):
        if not uploaded_files:
            st.warning("Por favor, adjunta al menos un documento.")
        else:
            # Guardar en sesión (simulado)
            new_app = {
                "property_id": prop["id"],
                "property_title": prop["title"],
                "applicant_name": user["name"],
                "applicant_email": user["email"],
                "comments": comments,
                "files": [f.name for f in uploaded_files],
                "status": "En revisión",
                "timestamp": pd.Timestamp.now()
            }

            # Guardar en lista global de solicitudes
            if "rental_applications" not in st.session_state:
                st.session_state.rental_applications = []
            st.session_state.rental_applications.append(new_app)

            st.success("✅ ¡Solicitud enviada con éxito!")
            st.info("El arrendador la revisará pronto. Puedes ver el estado en tu perfil.")
            st.balloons()

            # Opcional: volver al inicio después de 3 segundos
            if st.button("Volver al inicio"):
                st.session_state.current_page = "home"
                st.rerun()

    if st.button("⬅️ Volver"):
        st.session_state.current_page = "home"
        # No elimines selected_property, para que siga mostrando el detalle
        st.rerun()


# === Navegación principal ===
if not st.session_state.logged_in:
    show_auth()
else:
    # Estado de sesión
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "applications" not in st.session_state:
        st.session_state.applications = []  # ← ¡FALTABA ESTO!

    user = get_user(st.session_state.user_email)
    st.sidebar.title("Kyla")
    st.sidebar.markdown(f"👤 {user['name']}")

    # Define current_page si no existe
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    # Botones de navegación
    page = st.sidebar.radio("Ir a", ["Inicio", "Mi perfil"])

    if page == "Inicio":
        st.session_state.current_page = "home"
    elif page == "Mi perfil":
        st.session_state.current_page = "profile"

    # === Renderizado de páginas ===
    if st.session_state.current_page == "home":
        show_home()
        if "selected_property" in st.session_state:
            show_property_detail()

    elif st.session_state.current_page == "rental_application":
        show_rental_application()

    elif st.session_state.current_page == "profile":
        show_profile()