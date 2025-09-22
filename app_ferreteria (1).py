import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de la página
st.set_page_config(
    page_title="Hotel California - Sistema de Gestión",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conexión a PostgreSQL
@st.cache_resource
def init_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            database=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            port=st.secrets["DB_PORT"]
        )
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

conn = init_connection()

# Función para ejecutar consultas
def ejecutar_consulta(query, params=None):
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        result = cur.fetchall()
        conn.commit()
        cur.close()
        return result
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return None

# Autenticación
def login():
    st.sidebar.title("🏨 Hotel California")
    st.sidebar.markdown("*Welcome to the Hotel California*")
    st.sidebar.markdown("---")

    username = st.sidebar.text_input("Usuario", value="admin")
    password = st.sidebar.text_input("Contraseña", type="password", value="admin123")

    if st.sidebar.button("🔑 Ingresar", use_container_width=True):
        user_data = ejecutar_consulta(
            """
            SELECT username, nombre, rol
            FROM usuarios
            WHERE username = %s AND password = %s AND activo = true
            """,
            (username, password)
        )
        if user_data:
            st.session_state.logged_in = True
            st.session_state.user = {
                "username": user_data[0][0],
                "nombre": user_data[0][1],
                "rol": user_data[0][2]
            }
            st.rerun()
        else:
            st.sidebar.error("❌ Usuario o contraseña incorrectos")

# Dashboard principal
def dashboard():
    st.title("🏨 Dashboard - Hotel California")
    st.markdown("*Such a lovely place*")

    # Métricas del día
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ocupadas_hoy = ejecutar_consulta("""
            SELECT COUNT(*) FROM reservas r 
            WHERE %s BETWEEN r.fecha_checkin AND r.fecha_checkout 
            AND r.estado = 'confirmada'
        """, (date.today(),))
        total_habitaciones = ejecutar_consulta("SELECT COUNT(*) FROM habitaciones WHERE activa = true")
        ocupacion = (ocupadas_hoy[0][0] / total_habitaciones[0][0] * 100) if total_habitaciones[0][0] > 0 else 0
        st.metric("🛏️ Ocupación Hoy", f"{ocupacion:.1f}%")

    with col2:
        checkins_hoy = ejecutar_consulta("""
            SELECT COUNT(*) FROM reservas 
            WHERE fecha_checkin = %s AND estado = 'confirmada'
        """, (date.today(),))
        st.metric("📅 Check-ins Hoy", checkins_hoy[0][0] if checkins_hoy else 0)

    with col3:
        checkouts_hoy = ejecutar_consulta("""
            SELECT COUNT(*) FROM reservas 
            WHERE fecha_checkout = %s AND estado IN ('confirmada', 'en_estadia')
        """, (date.today(),))
        st.metric("🚪 Check-outs Hoy", checkouts_hoy[0][0] if checkouts_hoy else 0)

    with col4:
        ingresos_mes = ejecutar_consulta("""
            SELECT COALESCE(SUM(total), 0) FROM reservas 
            WHERE EXTRACT(MONTH FROM fecha_checkin) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM fecha_checkin) = EXTRACT(YEAR FROM CURRENT_DATE)
            AND estado != 'cancelada'
        """)
        st.metric("💰 Ingresos Mes", f"${ingresos_mes[0][0]:,.2f}" if ingresos_mes else "$0")

    st.markdown("---")

    # Gráficos
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏠 Ocupación por Tipo de Habitación")
        ocupacion_tipo = ejecutar_consulta("""
            SELECT h.tipo, 
                   COUNT(*) as total_habitaciones,
                   COUNT(CASE WHEN r.id IS NOT NULL THEN 1 END) as ocupadas
            FROM habitaciones h
            LEFT JOIN reservas r ON h.id = r.habitacion_id 
                AND %s BETWEEN r.fecha_checkin AND r.fecha_checkout
                AND r.estado = 'confirmada'
            WHERE h.activa = true
            GROUP BY h.tipo
        """, (date.today(),))
        
        if ocupacion_tipo:
            df_ocupacion = pd.DataFrame(ocupacion_tipo, columns=['Tipo', 'Total', 'Ocupadas'])
            df_ocupacion['Disponibles'] = df_ocupacion['Total'] - df_ocupacion['Ocupadas']
            
            fig = px.bar(df_ocupacion, x='Tipo', y=['Ocupadas', 'Disponibles'], 
                        title='Estado de Habitaciones por Tipo')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Reservas por Estado")
        reservas_estado = ejecutar_consulta("""
            SELECT estado, COUNT(*) as cantidad
            FROM reservas
            WHERE fecha_checkin >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY estado
        """)
        
        if reservas_estado:
            df_estado = pd.DataFrame(reservas_estado, columns=['Estado', 'Cantidad'])
            fig = px.pie(df_estado, values='Cantidad', names='Estado', 
                        title='Distribución de Reservas (Últimos 30 días)')
            st.plotly_chart(fig, use_container_width=True)

    # Próximas llegadas y salidas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Próximas Llegadas")
        llegadas = ejecutar_consulta("""
            SELECT r.numero_reserva, c.nombre, h.numero, r.fecha_checkin
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
            JOIN habitaciones h ON r.habitacion_id = h.id
            WHERE r.fecha_checkin BETWEEN %s AND %s
            AND r.estado = 'confirmada'
            ORDER BY r.fecha_checkin
            LIMIT 5
        """, (date.today(), date.today() + timedelta(days=2)))
        
        if llegadas:
            df_llegadas = pd.DataFrame(llegadas, columns=['Reserva', 'Cliente', 'Habitación', 'Fecha'])
            st.dataframe(df_llegadas, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🚪 Próximas Salidas")
        salidas = ejecutar_consulta("""
            SELECT r.numero_reserva, c.nombre, h.numero, r.fecha_checkout
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
            JOIN habitaciones h ON r.habitacion_id = h.id
            WHERE r.fecha_checkout BETWEEN %s AND %s
            AND r.estado IN ('confirmada', 'en_estadia')
            ORDER BY r.fecha_checkout
            LIMIT 5
        """, (date.today(), date.today() + timedelta(days=2)))
        
        if salidas:
            df_salidas = pd.DataFrame(salidas, columns=['Reserva', 'Cliente', 'Habitación', 'Fecha'])
            st.dataframe(df_salidas, use_container_width=True, hide_index=True)

# Módulo de reservas
def modulo_reservas():
    st.title("📋 Gestión de Reservas")

    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito

    tab1, tab2, tab3 = st.tabs(["Lista de Reservas", "Nueva Reserva", "Verificar Disponibilidad"])

    with tab1:
        st.subheader("📋 Reservas Registradas")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_estado = st.selectbox("Estado", ["Todas", "confirmada", "en_estadia", "finalizada", "cancelada"])
        with col2:
            filtro_fecha = st.date_input("Desde fecha", value=date.today() - timedelta(days=7))
        with col3:
            buscar_cliente = st.text_input("🔍 Buscar cliente")

        # Consulta con filtros
        query = """
            SELECT r.numero_reserva, c.nombre, h.numero, h.tipo,
                   r.fecha_checkin, r.fecha_checkout, r.noches,
                   r.total, r.estado, r.fecha_creacion
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
            JOIN habitaciones h ON r.habitacion_id = h.id
            WHERE r.fecha_checkin >= %s
        """
        params = [filtro_fecha]

        if filtro_estado != "Todas":
            query += " AND r.estado = %s"
            params.append(filtro_estado)

        if buscar_cliente:
            query += " AND c.nombre ILIKE %s"
            params.append(f"%{buscar_cliente}%")

        query += " ORDER BY r.fecha_creacion DESC"

        reservas = ejecutar_consulta(query, params)
        
        if reservas:
            df_reservas = pd.DataFrame(reservas, columns=[
                'Reserva', 'Cliente', 'Habitación', 'Tipo', 'Check-in', 
                'Check-out', 'Noches', 'Total', 'Estado', 'Fecha Creación'
            ])
            
            st.dataframe(
                df_reservas,
                column_config={
                    "Total": st.column_config.NumberColumn(format="$%.2f"),
                    "Check-in": st.column_config.DateColumn(),
                    "Check-out": st.column_config.DateColumn(),
                    "Estado": st.column_config.TextColumn()
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No se encontraron reservas con los criterios seleccionados")

    with tab2:
        st.subheader("➕ Nueva Reserva")

        with st.form("form_nueva_reserva"):
            col1, col2 = st.columns(2)

            with col1:
                # Seleccionar cliente
                clientes = ejecutar_consulta("SELECT id, cedula, nombre FROM clientes ORDER BY nombre")
                if clientes:
                    cliente_opts = {f"{c[1]} - {c[2]}": c[0] for c in clientes}
                    cliente_seleccionado = st.selectbox("Cliente*", options=list(cliente_opts.keys()))
                else:
                    st.error("No hay clientes registrados. Registra un cliente primero.")
                    cliente_seleccionado = None

                fecha_checkin = st.date_input("Fecha Check-in*", value=date.today() + timedelta(days=1))
                fecha_checkout = st.date_input("Fecha Check-out*", value=date.today() + timedelta(days=2))

            with col2:
                # Tipo de habitación
                tipos_habitacion = ejecutar_consulta("SELECT DISTINCT tipo FROM habitaciones WHERE activa = true")
                if tipos_habitacion:
                    tipo_habitacion = st.selectbox("Tipo de Habitación*", [t[0] for t in tipos_habitacion])
                else:
                    st.error("No hay tipos de habitación disponibles")
                    tipo_habitacion = None

                huespedes = st.number_input("Número de Huéspedes", min_value=1, max_value=6, value=1)
                observaciones = st.text_area("Observaciones")

            if st.form_submit_button("💾 Crear Reserva", use_container_width=True):
                if cliente_seleccionado and fecha_checkin and fecha_checkout and tipo_habitacion:
                    if fecha_checkout <= fecha_checkin:
                        st.error("❌ La fecha de check-out debe ser posterior al check-in")
                    else:
                        cliente_id = cliente_opts[cliente_seleccionado]
                        noches = (fecha_checkout - fecha_checkin).days

                        # Verificar disponibilidad
                        habitacion_disponible = ejecutar_consulta("""
                            SELECT h.id, h.numero, h.precio_noche
                            FROM habitaciones h
                            WHERE h.tipo = %s AND h.activa = true
                            AND h.id NOT IN (
                                SELECT r.habitacion_id
                                FROM reservas r
                                WHERE r.estado IN ('confirmada', 'en_estadia')
                                AND NOT (r.fecha_checkout <= %s OR r.fecha_checkin >= %s)
                            )
                            LIMIT 1
                        """, (tipo_habitacion, fecha_checkin, fecha_checkout))

                        if habitacion_disponible:
                            habitacion_id = habitacion_disponible[0][0]
                            numero_habitacion = habitacion_disponible[0][1]
                            precio_noche = habitacion_disponible[0][2]
                            total = precio_noche * noches

                            # Generar número de reserva
                            numero_reserva = f"RES{datetime.now().strftime('%Y%m%d%H%M%S')}"

                            # Insertar reserva
                            ejecutar_consulta("""
                                INSERT INTO reservas (numero_reserva, cliente_id, habitacion_id,
                                                    fecha_checkin, fecha_checkout, noches, huespedes,
                                                    total, observaciones, estado)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmada')
                            """, (numero_reserva, cliente_id, habitacion_id, fecha_checkin,
                                  fecha_checkout, noches, huespedes, total, observaciones))

                            st.session_state.mensaje_exito = f"✅ Reserva {numero_reserva} creada exitosamente. Habitación: {numero_habitacion}"
                            st.rerun()
                        else:
                            st.error("❌ No hay habitaciones disponibles para las fechas seleccionadas")
                else:
                    st.error("❌ Todos los campos marcados con * son obligatorios")

    with tab3:
        st.subheader("🔍 Verificar Disponibilidad")

        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio", value=date.today())
        with col2:
            fecha_fin = st.date_input("Fecha fin", value=date.today() + timedelta(days=1))
        with col3:
            tipo_filtro = st.selectbox("Tipo de habitación", ["Todas"] + [t[0] for t in tipos_habitacion] if tipos_habitacion else ["Todas"])

        if st.button("🔍 Verificar Disponibilidad", use_container_width=True):
            if fecha_fin <= fecha_inicio:
                st.error("❌ La fecha fin debe ser posterior a la fecha inicio")
            else:
                query_disponibilidad = """
                    SELECT h.numero, h.tipo, h.capacidad, h.precio_noche,
                           CASE WHEN r.id IS NULL THEN 'Disponible' ELSE 'Ocupada' END as estado
                    FROM habitaciones h
                    LEFT JOIN reservas r ON h.id = r.habitacion_id
                        AND r.estado IN ('confirmada', 'en_estadia')
                        AND NOT (r.fecha_checkout <= %s OR r.fecha_checkin >= %s)
                    WHERE h.activa = true
                """
                params = [fecha_inicio, fecha_fin]

                if tipo_filtro != "Todas":
                    query_disponibilidad += " AND h.tipo = %s"
                    params.append(tipo_filtro)

                query_disponibilidad += " ORDER BY h.numero"

                disponibilidad = ejecutar_consulta(query_disponibilidad, params)

                if disponibilidad:
                    df_disponibilidad = pd.DataFrame(disponibilidad, columns=[
                        'Habitación', 'Tipo', 'Capacidad', 'Precio/Noche', 'Estado'
                    ])

                    # Aplicar colores según disponibilidad
                    def color_estado(val):
                        color = 'lightgreen' if val == 'Disponible' else 'lightcoral'
                        return f'background-color: {color}'

                    styled_df = df_disponibilidad.style.applymap(
                        color_estado, subset=['Estado']
                    )

                    st.dataframe(styled_df, use_container_width=True, hide_index=True)

                    # Estadísticas
                    disponibles = len(df_disponibilidad[df_disponibilidad['Estado'] == 'Disponible'])
                    ocupadas = len(df_disponibilidad[df_disponibilidad['Estado'] == 'Ocupada'])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("🟢 Disponibles", disponibles)
                    col2.metric("🔴 Ocupadas", ocupadas)
                    col3.metric("📊 Ocupación", f"{(ocupadas/(disponibles+ocupadas)*100):.1f}%" if (disponibles+ocupadas) > 0 else "0%")

# Módulo de check-in/check-out
def modulo_checkin_checkout():
    st.title("🔑 Check-in / Check-out")

    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito

    tab1, tab2 = st.tabs(["Check-in", "Check-out"])

    with tab1:
        st.subheader("📅 Check-in de Huéspedes")

        # Reservas programadas para hoy o anteriores sin check-in
        reservas_checkin = ejecutar_consulta("""
            SELECT r.id, r.numero_reserva, c.nombre, h.numero, h.tipo,
                   r.fecha_checkin, r.huespedes, r.total
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
            JOIN habitaciones h ON r.habitacion_id = h.id
            WHERE r.estado = 'confirmada'
            AND r.fecha_checkin <= %s
            ORDER BY r.fecha_checkin, r.numero_reserva
        """, (date.today(),))

        if reservas_checkin:
            st.subheader("Reservas pendientes de check-in:")
            
            for reserva in reservas_checkin:
                with st.expander(f"Reserva {reserva[1]} - {reserva[2]} - Habitación {reserva[3]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Cliente:** {reserva[2]}")
                        st.write(f"**Habitación:** {reserva[3]} ({reserva[4]})")
                        st.write(f"**Fecha programada:** {reserva[5]}")
                    
                    with col2:
                        st.write(f"**Huéspedes:** {reserva[6]}")
                        st.write(f"**Total:** ${reserva[7]:,.2f}")
                    
                    with st.form(f"checkin_{reserva[0]}"):
                        observaciones_checkin = st.text_area("Observaciones del check-in", key=f"obs_checkin_{reserva[0]}")
                        
                        if st.form_submit_button("✅ Realizar Check-in", use_container_width=True):
                            # Actualizar estado de la reserva
                            ejecutar_consulta("""
                                UPDATE reservas 
                                SET estado = 'en_estadia',
                                    checkin_real = CURRENT_TIMESTAMP,
                                    observaciones = COALESCE(observaciones, '') || %s
                                WHERE id = %s
                            """, (f"\nCheck-in: {observaciones_checkin}", reserva[0]))
                            
                            st.session_state.mensaje_exito = f"✅ Check-in realizado para reserva {reserva[1]}"
                            st.rerun()
        else:
            st.info("No hay reservas pendientes de check-in para hoy")

    with tab2:
        st.subheader("🚪 Check-out de Huéspedes")

        # Reservas en estadía que deben hacer checkout hoy o ya deberían haber salido
        reservas_checkout = ejecutar_consulta("""
            SELECT r.id, r.numero_reserva, c.nombre, h.numero, h.tipo,
                   r.fecha_checkout, r.total, r.checkin_real
            FROM reservas r
            JOIN clientes c ON r.cliente_id = c.id
            JOIN habitaciones h ON r.habitacion_id = h.id
            WHERE r.estado = 'en_estadia'
            AND r.fecha_checkout <= %s + INTERVAL '1 day'
            ORDER BY r.fecha_checkout, r.numero_reserva
        """, (date.today(),))

        if reservas_checkout:
            st.subheader("Huéspedes para check-out:")
            
            for reserva in reservas_checkout:
                fecha_checkout = reserva[5]
                es_tarde = fecha_checkout < date.today()
                
                with st.expander(f"{'🔴 TARDE - ' if es_tarde else ''}Reserva {reserva[1]} - {reserva[2]} - Habitación {reserva[3]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Cliente:** {reserva[2]}")
                        st.write(f"**Habitación:** {reserva[3]} ({reserva[4]})")
                        st.write(f"**Check-out programado:** {reserva[5]}")
                        if es_tarde:
                            st.error("⚠️ Check-out atrasado")
                    
                    with col2:
                        st.write(f"**Total:** ${reserva[6]:,.2f}")
                        st.write(f"**Check-in realizado:** {reserva[7].strftime('%Y-%m-%d %H:%M') if reserva[7] else 'N/A'}")
                    
                    with st.form(f"checkout_{reserva[0]}"):
                        observaciones_checkout = st.text_area("Observaciones del check-out", key=f"obs_checkout_{reserva[0]}")
                        
                        # Opcional: cargos adicionales
                        cargos_adicionales = st.number_input("Cargos adicionales", min_value=0.0, step=0.1, key=f"cargos_{reserva[0]}")
                        
                        if st.form_submit_button("✅ Realizar Check-out", use_container_width=True):
                            total_final = reserva[6] + cargos_adicionales
                            
                            # Actualizar estado de la reserva
                            ejecutar_consulta("""
                                UPDATE reservas 
                                SET estado = 'finalizada',
                                    checkout_real = CURRENT_TIMESTAMP,
                                    total = %s,
                                    observaciones = COALESCE(observaciones, '') || %s
                                WHERE id = %s
                            """, (total_final, f"\nCheck-out: {observaciones_checkout}", reserva[0]))
                            
                            st.session_state.mensaje_exito = f"✅ Check-out realizado para reserva {reserva[1]}. Total final: ${total_final:,.2f}"
                            st.rerun()
        else:
            st.info("No hay huéspedes pendientes de check-out")

# Módulo de clientes
def modulo_clientes():
    st.title("👥 Gestión de Clientes")

    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito

    tab1, tab2, tab3 = st.tabs(["Lista de Clientes", "Registrar Cliente", "Historial"])

    with tab1:
        st.subheader("📋 Clientes Registrados")

        buscar_cliente = st.text_input("🔍 Buscar cliente")
        
        query = """
            SELECT c.cedula, c.nombre, c.telefono, c.email,
                   c.fecha_registro,
                   COUNT(r.id) as total_reservas,
                   COALESCE(SUM(CASE WHEN r.estado != 'cancelada' THEN r.total ELSE 0 END), 0) as total_gastado
            FROM clientes c
            LEFT JOIN reservas r ON c.id = r.cliente_id
        """
        params = []

        if buscar_cliente:
            query += " WHERE (c.nombre ILIKE %s OR c.cedula ILIKE %s)"
            params.extend([f"%{buscar_cliente}%", f"%{buscar_cliente}%"])

        query += " GROUP BY c.id, c.cedula, c.nombre, c.telefono, c.email, c.fecha_registro ORDER BY c.nombre"

        clientes = ejecutar_consulta(query, params) if params else ejecutar_consulta(query)

        if clientes:
            df_clientes = pd.DataFrame(clientes, columns=[
                'Cédula', 'Nombre', 'Teléfono', 'Email', 'Fecha Registro', 'Total Reservas', 'Total Gastado'
            ])

            st.dataframe(
                df_clientes,
                column_config={
                    "Total Gastado": st.column_config.NumberColumn(format="$%.2f"),
                    "Fecha Registro": st.column_config.DatetimeColumn(format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No se encontraron clientes")

    with tab2:
        st.subheader("➕ Registrar Nuevo Cliente")

        with st.form("form_nuevo_cliente"):
            col1, col2 = st.columns(2)

            with col1:
                cedula = st.text_input("Cédula/DNI*", max_chars=20)
                nombre = st.text_input("Nombre Completo*", max_chars=100)
                telefono = st.text_input("Teléfono", max_chars=20)

            with col2:
                email = st.text_input("Email", max_chars=100)
                direccion = st.text_area("Dirección")
                nacionalidad = st.text_input("Nacionalidad")

            if st.form_submit_button("💾 Registrar Cliente", use_container_width=True):
                if cedula and nombre:
                    # Verificar si ya existe
                    existe = ejecutar_consulta("SELECT id FROM clientes WHERE cedula = %s", (cedula,))
                    if existe:
                        st.error("❌ Ya existe un cliente con esta cédula")
                    else:
                        ejecutar_consulta("""
                            INSERT INTO clientes (cedula, nombre, telefono, email, direccion, nacionalidad)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (cedula, nombre, telefono, email, direccion, nacionalidad))
                        
                        st.session_state.mensaje_exito = "✅ Cliente registrado exitosamente"
                        st.rerun()
                else:
                    st.error("❌ Cédula y Nombre son obligatorios")

    with tab3:
        st.subheader("📋 Historial de Estadías")

        clientes_con_reservas = ejecutar_consulta("""
            SELECT DISTINCT c.id, c.cedula, c.nombre 
            FROM clientes c
            JOIN reservas r ON c.id = r.cliente_id
            ORDER BY c.nombre
        """)

        if clientes_con_reservas:
            cliente_opts = {f"{c[1]} - {c[2]}": c[0] for c in clientes_con_reservas}
            cliente_hist = st.selectbox("Seleccionar Cliente", options=list(cliente_opts.keys()))

            if cliente_hist:
                cliente_id = cliente_opts[cliente_hist]

                reservas_cliente = ejecutar_consulta("""
                    SELECT r.numero_reserva, h.numero, h.tipo,
                           r.fecha_checkin, r.fecha_checkout, r.noches,
                           r.total, r.estado, r.checkin_real, r.checkout_real
                    FROM reservas r
                    JOIN habitaciones h ON r.habitacion_id = h.id
                    WHERE r.cliente_id = %s
                    ORDER BY r.fecha_checkin DESC
                """, (cliente_id,))

                if reservas_cliente:
                    df_reservas = pd.DataFrame(reservas_cliente, columns=[
                        'Reserva', 'Habitación', 'Tipo', 'Check-in', 'Check-out', 
                        'Noches', 'Total', 'Estado', 'Check-in Real', 'Check-out Real'
                    ])

                    st.dataframe(
                        df_reservas,
                        column_config={
                            "Total": st.column_config.NumberColumn(format="$%.2f"),
                            "Check-in": st.column_config.DateColumn(),
                            "Check-out": st.column_config.DateColumn(),
                            "Check-in Real": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                            "Check-out Real": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                    # Estadísticas del cliente
                    total_gastado = sum(r[6] for r in reservas_cliente if r[7] != 'cancelada')
                    total_noches = sum(r[5] for r in reservas_cliente if r[7] != 'cancelada')
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Gastado", f"${total_gastado:,.2f}")
                    col2.metric("Total Reservas", len(reservas_cliente))
                    col3.metric("Total Noches", total_noches)
                else:
                    st.info("Este cliente no tiene reservas registradas")
        else:
            st.info("No hay clientes con historial de reservas")

# Perfil de usuario
def perfil_usuario():
    st.title("👤 Mi Perfil")
    user = st.session_state.user

    st.subheader("Información del Usuario")
    st.write(f"**Usuario:** {user['username']}")
    st.write(f"**Nombre:** {user['nombre']}")
    st.write(f"**Rol:** {user['rol']}")

    with st.form("form_editar_perfil"):
        nuevo_nombre = st.text_input("Nombre", value=user['nombre'])
        nuevo_email = st.text_input("Email", value=user.get('email', ""))
        nueva_password = st.text_input("Nueva Contraseña", type="password")

        if st.form_submit_button("💾 Actualizar Perfil"):
            ejecutar_consulta("""
                UPDATE usuarios
                SET nombre = %s, email = %s, password = COALESCE(NULLIF(%s,''), password)
                WHERE username = %s
            """, (nuevo_nombre, nuevo_email, nueva_password, user['username']))
            st.success("✅ Perfil actualizado exitosamente")
            st.session_state.user['nombre'] = nuevo_nombre
            st.session_state.user['email'] = nuevo_email

# Navegación principal
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.title(f"👋 Bienvenido, {st.session_state.user['nombre']}")
        st.sidebar.markdown(f"**Rol:** {st.session_state.user['rol']}")
        st.sidebar.markdown("---")

        rol = st.session_state.user['rol']

        # Menú dinámico según rol
        if rol == "admin":
            menu = st.sidebar.selectbox(
                "📋 Navegación",
                ["Dashboard", "Reservas", "Check-in/Check-out", "Clientes", "Perfil"]
            )
        elif rol == "recepcionista":
            menu = st.sidebar.selectbox(
                "📋 Navegación",
                ["Reservas", "Check-in/Check-out", "Clientes", "Perfil"]
            )
        elif rol == "gerente":
            menu = st.sidebar.selectbox(
                "📋 Navegación",
                ["Dashboard", "Reservas", "Clientes", "Perfil"]
            )
        else:
            st.error("🚫 Rol no reconocido")
            return

        # Cargar módulos según menú y permisos
        if menu == "Dashboard":
            if rol in ["admin", "gerente"]:
                dashboard()
            else:
                st.error("🚫 No tienes permiso para acceder al Dashboard")

        elif menu == "Reservas":
            if rol in ["admin", "recepcionista", "gerente"]:
                modulo_reservas()
            else:
                st.error("🚫 No tienes permiso para gestionar reservas")

        elif menu == "Check-in/Check-out":
            if rol in ["admin", "recepcionista"]:
                modulo_checkin_checkout()
            else:
                st.error("🚫 No tienes permiso para realizar check-in/check-out")

        elif menu == "Clientes":
            if rol in ["admin", "recepcionista", "gerente"]:
                modulo_clientes()
            else:
                st.error("🚫 No tienes permiso para gestionar clientes")

        elif menu == "Perfil":
            perfil_usuario()

        st.sidebar.markdown("---")
        st.sidebar.info("""
        🏨 **Hotel California**
        *"You can check out any time you like,
        but you can never leave!"*
        """)
        
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    main()
