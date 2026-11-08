# Secretaría Virtual Académica — CRUC Coclé

Aplicación web para la gestión académica de la Universidad Distribuida 360°.
El proyecto separa la API REST (FastAPI + PostgreSQL) de la interfaz NiceGUI.

## Arquitectura

```
Arquitectura/
├── backend/
│   ├── secretaria_api/          # API FastAPI, modelos SQLAlchemy, servicios y seed
│   ├── alembic/                 # Migraciones de base de datos
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── secretaria_ui/           # Interfaz NiceGUI que consume la API
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

- **Backend:** `http://localhost:8000` — documentación interactiva en `/docs`.
- **Frontend:** `http://localhost:8080`.
- **Base de datos:** PostgreSQL 16, base `secretaria_virtual`.

## Inicio rápido con Docker

Requisitos: Docker y Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

El backend aplica las migraciones de Alembic y ejecuta el seed de forma
idempotente al iniciar. Luego abra <http://localhost:8080>.

Para detener:

```bash
docker compose down
```

Para eliminar también los datos:

```bash
docker compose down -v
```

## Ejecución local (sin Docker)

1. Cree un entorno virtual e instale dependencias:

```bash
python3 -m venv up
source up/bin/activate
pip install -r backend/requirements.txt -r frontend/requirements.txt
```

2. Cree la base de datos PostgreSQL:

```bash
createdb secretaria_virtual
```

3. Ajuste `DATABASE_URL` en `.env` si es necesario:

```dotenv
DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/secretaria_virtual
```

4. Aplique migraciones y cargue los datos iniciales:

```bash
cd backend
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. python -m secretaria_api.seed
```

5. Inicie el backend:

```bash
cd backend
PYTHONPATH=. uvicorn secretaria_api.main:app --reload --port 8000
```

6. En otra terminal, inicie el frontend:

```bash
PYTHONPATH=frontend uvicorn secretaria_ui.main:app --host 0.0.0.0 --port 8080
```

Abra <http://localhost:8080>.

### Entorno local restringido (sin CREATEDB)

Si su usuario no puede crear bases de datos, puede usar una base existente con
un esquema dedicado:

```bash
psql -d simplex -c "CREATE SCHEMA IF NOT EXISTS secretaria_virtual AUTHORIZATION moises;"

cd backend
DATABASE_URL='postgresql+psycopg://moises@/simplex' \
PGOPTIONS='-c search_path=secretaria_virtual' \
PYTHONPATH=. alembic upgrade head

DATABASE_URL='postgresql+psycopg://moises@/simplex' \
PGOPTIONS='-c search_path=secretaria_virtual' \
PYTHONPATH=. python -m secretaria_api.seed
```

Use las mismas variables al iniciar uvicorn.

## Credenciales de demostración

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador | `admin@universidad.edu.pa` | `password123` |
| Estudiante | `estudiante@universidad.edu.pa` | `password123` |
| Secretaría | `secretaria@universidad.edu.pa` | `password123` |
| Profesor | `ana.gomez@universidad.edu.pa` | `password123` |
| Profesor | `luis.perez@universidad.edu.pa` | `password123` |
| Estudiante | `juan.batista@universidad.edu.pa` | `password123` |

Cédulas de acceso: administrador `ADMIN-01`, estudiante `8-888-8888`.

## Funcionalidades principales

- Autenticación por correo/cédula con roles: administrador, administrador de
  facultad, coordinador, secretaría, profesor y estudiante.
- Dashboard administrativo y dashboard del estudiante.
- Estructura académica: sedes, facultades, escuelas, carreras, planes,
  materias, períodos, aulas y grupos.
- Matrícula con validación de prerrequisitos, cupos, choques de horario,
  límite de créditos y períodos abiertos.
- Calificaciones, pagos, usuarios, permisos y auditoría de cambios.
- Módulo de infraestructura distribuida: nodos, replicación, fragmentación,
  transacciones 2PC, concurrencia, consultas globales, recuperación y
  diccionario de datos.

## Reglas de matrícula

- Los prerrequisitos se aprueban con `nota_final >= 71`.
- El cupo de un grupo cuenta solo matrículas en estado `inscrito`.
- Se rechazan choques de horario por día y solapamiento de horas.
- El límite de créditos se toma de `PeriodoAcademico.max_creditos`.
- Una matrícula confirmada no puede modificarse.
- Cada cambio de matrícula genera un registro de auditoría.

## API

- `GET /health` — estado del servicio.
- `GET /docs` — Swagger UI.
- `POST /api/auth/login` — inicio de sesión.
- `POST /api/auth/register` — registro de estudiante.
- `GET /api/auth/me` — usuario autenticado.
- `GET /api/dashboard/summary` y `/api/dashboard/student`.
- `GET /api/academic/*` — catálogo académico.
- `GET/POST/DELETE /api/enrollments*` — matrícula.
- `GET /api/grades/*`, `GET /api/payments*`.
- `GET/POST /api/users*` — usuarios y permisos.
- `GET /api/infrastructure/*` — monitoreo distribuido.

Los endpoints protegidos esperan `Authorization: Bearer <token>`.

## Notas de desarrollo

- Las contraseñas se almacenan con PBKDF2-HMAC-SHA256.
- Los tokens se firman con `itsdangerous` usando `SECRET_KEY`.
- El seed es idempotente: puede ejecutarse varias veces sin duplicar datos.
- Para pruebas del frontend sin navegador se puede usar `nicegui.testing.User`
  con `httpx.ASGITransport`.
