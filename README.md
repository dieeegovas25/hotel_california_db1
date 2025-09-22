Perfecto 🙌 Te preparo un **README.md** inicial para tu proyecto del **Sistema de Gestión Hotelera (Hotel California)**. Incluye: descripción, requisitos, instalación, ejecución, base de datos y control de versiones.

---

# 📌 README.md – Hotel California

## 🏨 Hotel California – Sistema de Gestión Hotelera

Este proyecto es un sistema de gestión para hoteles desarrollado en **Python + Streamlit**, con conexión a **PostgreSQL**.
Permite administrar reservas, clientes, habitaciones, check-in, check-out y generar reportes de ocupación e ingresos.

---

## 🚀 Características principales

* **Autenticación de usuarios** con roles (administrador, recepcionista).
* **Gestión de reservas**: creación, listado, disponibilidad de habitaciones.
* **Gestión de clientes**: registro, historial de reservas.
* **Check-in y Check-out** de huéspedes.
* **Dashboard** con métricas y gráficos de ocupación e ingresos.
* **Integración con PostgreSQL** para persistencia de datos.

---

## 🛠️ Requisitos

* Python 3.9+
* PostgreSQL 12+
* Dependencias de Python:

  ```bash
  pip install streamlit psycopg2-binary pandas plotly
  ```

---

## 📂 Instalación

1. Clona este repositorio:

   ```bash
   git clone https://github.com/tu_usuario/hotel-california.git
   cd hotel-california
   ```

2. Configura la base de datos en PostgreSQL:

   ```sql
   CREATE DATABASE hotel_california_db;
   ```

3. Ejecuta el script SQL (`hotel_california_db.sql`) para crear las tablas y datos iniciales.

---

## ▶️ Ejecución

Ejecuta la aplicación con:

```bash
streamlit run app.py
```

Accede en tu navegador a:

```
http://localhost:8501
```

---

## 🗄️ Base de Datos

El proyecto utiliza PostgreSQL con las siguientes tablas principales:

* **usuarios** → Control de acceso y roles.
* **clientes** → Información de huéspedes.
* **habitaciones** → Datos de las habitaciones disponibles.
* **reservas** → Gestión de reservas, check-in y check-out.

Usuario inicial:

```
Usuario: admin
Contraseña: admin123
```

---

## 📌 Control de versiones

Este proyecto utiliza **Git** como sistema de control de versiones.

* `main` → Rama estable para producción.
* `develop` → Rama de desarrollo.
* `feature/*` → Ramas para nuevas funcionalidades.
* `bugfix/*` → Ramas para corrección de errores.

Ejemplo de flujo de trabajo:

```bash
# Crear una rama para nueva funcionalidad
git checkout -b feature/gestion-reportes

# Subir cambios
git add .
git commit -m "Agregada funcionalidad de reportes de ocupación"
git push origin feature/gestion-reportes

# Fusionar a develop
git checkout develop
git merge feature/gestion-reportes
```

---

## 📜 Licencia

Este proyecto es de uso académico y libre bajo la licencia **MIT**.

---

