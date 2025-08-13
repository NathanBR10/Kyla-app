import streamlit as st
import pandas as pd
import os
from PIL import Image

# Configuración
st.set_page_config(page_title="Kyla", layout="wide")
st.markdown("<h1 style='text-align: center; color: #4A90E2;'>🏡 Kyla</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Encuentra o publica tu próximo hogar</p>",
            unsafe_allow_html=True)


# Cargar datos
@st.cache_data
def load_data():
    properties = pd.read_csv("data/properties.csv")
    users = pd.read_csv("data/users.csv")

    # Aseguramos que la contraseña sea string
    users["password"] = users["password"].astype(str)

    return properties, users


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
    st.markdown("### 🏠 Encuentra tu próximo hogar")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Buscar por ubicación o nombre")
    with col2:
        min_price = st.number_input("Precio mínimo", 0, 10000000, 0)
    with col3:
        max_price = st.number_input("Precio máximo", 0, 10000000, 1000000)

    filtered = properties_df.copy()
    if search:
        filtered = filtered[
            filtered["title"].str.contains(search, case=False) |
            filtered["location"].str.contains(search, case=False)
            ]
    filtered = filtered[(filtered["price"] >= min_price) & (filtered["price"] <= max_price)]

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
    prop = properties_df[properties_df["id"] == prop_id].iloc[0]
    owner = users_df[users_df["id"] == prop["owner_id"]].iloc[0]

    st.image([f"assets/images/{img}" for img in prop["images"].split(",")], width=300)
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


# Mi perfil
def show_profile():
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


# Navegación
if not st.session_state.logged_in:
    show_auth()
else:
    user = get_user(st.session_state.user_email)
    st.sidebar.title("Kyla")
    st.sidebar.markdown(f"👤 {user['name']}")
    page = st.sidebar.radio("Ir a", ["Inicio", "Mi perfil", "Publicar inmueble"])

    if page == "Inicio":
        show_home()
        if "selected_property" in st.session_state:
            show_property_detail()
    elif page == "Mi perfil":
        show_profile()
    elif page == "Publicar inmueble":
        if user["is_owner"]:
            show_add_property()
        else:
            st.warning("Debes registrarte como arrendador para publicar inmuebles.")