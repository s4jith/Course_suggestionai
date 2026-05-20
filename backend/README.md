# Academic Lesson Plan API

Production-ready backend for an AI-powered academic lesson plan management system built with FastAPI, MongoDB, and JWT authentication.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Runtime | Python 3.11+ |
| Database | MongoDB (Motor async driver) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validation | Pydantic v2 |
| Config | pydantic-settings + python-dotenv |
| Server | Uvicorn (ASGI) |

---

## Project Structure

```
backend/
├── venv/                                       # Python virtual environment (not committed)
├── app/
│   ├── main.py                                 # Application factory + lifespan hooks
│   ├── config/
│   │   └── settings.py                         # Pydantic settings loaded from .env
│   ├── database/
│   │   └── mongodb.py                          # Motor client singleton + get_database dependency
│   ├── models/
│   │   ├── user.py                             # UserDocument, UserRole, PyObjectId
│   │   └── lesson_plan.py                      # SubjectDocument, LessonPlanDocument, TopicProgressDocument
│   ├── schemas/
│   │   ├── user.py                             # User request/response schemas
│   │   ├── token.py                            # JWT token schemas
│   │   └── lesson_plan.py                      # Lesson plan request/response + analytics schemas
│   ├── routes/
│   │   ├── auth.py                             # /api/v1/auth/**
│   │   ├── users.py                            # /api/v1/users/**
│   │   ├── subjects.py                         # /api/v1/subjects/**
│   │   ├── lesson_plans.py                     # /api/v1/lesson-plans/**
│   │   └── topic_progress.py                   # /api/v1/topic-progress/**
│   ├── services/
│   │   ├── auth_service.py                     # Registration, login, token refresh
│   │   └── lesson_plan_service.py              # Subject, plan, progress business logic
│   ├── repositories/
│   │   ├── user_repository.py                  # users collection I/O
│   │   ├── subject_repository.py               # subjects collection I/O
│   │   ├── lesson_plan_repository.py           # lesson_plans collection I/O
│   │   └── topic_progress_repository.py        # topic_progress collection I/O
│   ├── auth/
│   │   ├── jwt_handler.py                      # Token creation and decoding
│   │   └── dependencies.py                     # Auth dependencies + RBAC helpers
│   ├── middleware/
│   │   └── logging_middleware.py               # Access log middleware (X-Request-ID)
│   ├── utils/
│   │   └── password.py                         # bcrypt hash / verify / needs_rehash
│   └── core/
│       ├── exceptions.py                       # Typed HTTP exceptions
│       └── responses.py                        # Standard JSON response envelopes
├── requirements.txt
├── .env                                        # Local secrets (never commit)
├── .env.example                                # Template for .env
└── README.md
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11 or higher
- MongoDB running locally on port 27017 (or a MongoDB Atlas URI)

### 2. Create and activate the virtual environment

```bash
# Windows
cd backend
python -m venv venv
venv\Scripts\activate

# macOS / Linux
cd backend
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Generate a secure JWT secret:

```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

### 5. Run the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open interactive docs

```
http://localhost:8000/docs    # Swagger UI (DEBUG=true only)
http://localhost:8000/redoc   # ReDoc     (DEBUG=true only)
```

---

## Authentication API

### Base URL

```
http://localhost:8000/api/v1
```

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login and receive JWT tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### Register

```
POST /api/v1/auth/register
```

```json
{
  "email": "teacher@school.edu",
  "full_name": "Alice Johnson",
  "password": "SecurePass1!",
  "role": "teacher"
}
```

### Login

```
POST /api/v1/auth/login
```

```json
{
  "email": "teacher@school.edu",
  "password": "SecurePass1!"
}
```

Response:
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

## Lesson Plan Management Module

### Collections

| Collection | Description |
|---|---|
| `subjects` | Academic subjects (name, code, department, semester, hours) |
| `lesson_plans` | Full hierarchical plan embedding chapters -> topics -> subtopics |
| `topic_progress` | Per-teacher topic completion records with teaching details |

### MongoDB Document Examples

**subjects**
```json
{
  "_id": "ObjectId(...)",
  "name": "Data Structures",
  "code": "CS301",
  "description": "Fundamental data structures and algorithms",
  "department": "Computer Science",
  "semester": 3,
  "total_hours": 60,
  "is_active": true,
  "created_by": "683abc000def000000000001",
  "updated_by": "683abc000def000000000001",
  "created_at": "2026-05-20T10:00:00",
  "updated_at": "2026-05-20T10:00:00"
}
```

**lesson_plans** (embedded hierarchy)
```json
{
  "_id": "ObjectId(...)",
  "subject_id": "683abc111def456789011111",
  "teacher_id": "683abc000def000000000001",
  "academic_year": "2025-26",
  "semester": 3,
  "title": "DS Full Semester Plan",
  "status": "active",
  "chapters": [
    {
      "chapter_id": "uuid-string",
      "title": "Linked Lists",
      "order": 1,
      "topics": [
        {
          "topic_id": "uuid-string",
          "title": "Singly Linked List",
          "planned_hours": 2.0,
          "planned_date": "2026-06-10T09:00:00",
          "order": 1,
          "subtopics": [
            { "subtopic_id": "uuid-string", "title": "Insertion", "order": 1 },
            { "subtopic_id": "uuid-string", "title": "Deletion", "order": 2 }
          ]
        }
      ]
    }
  ],
  "created_by": "683abc000def000000000001",
  "updated_by": "683abc000def000000000001",
  "created_at": "2026-05-20T10:00:00",
  "updated_at": "2026-05-20T10:00:00"
}
```

**topic_progress**
```json
{
  "_id": "ObjectId(...)",
  "lesson_plan_id": "683abc123def456789012345",
  "chapter_id": "uuid-string",
  "topic_id": "uuid-string",
  "subtopic_id": null,
  "teacher_id": "683abc000def000000000001",
  "subject_id": "683abc111def456789011111",
  "status": "completed",
  "completion_percentage": 100.0,
  "teaching_method": "ppt",
  "actual_date": "2026-05-20T10:00:00",
  "duration_taken": 1.5,
  "student_understanding_level": "good",
  "remarks": "Covered all insertion and deletion cases.",
  "issues": null,
  "created_by": "683abc000def000000000001",
  "updated_by": "683abc000def000000000001",
  "created_at": "2026-05-20T10:05:00",
  "updated_at": "2026-05-20T10:05:00"
}
```

### Subject API

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/subjects/` | Teacher/Admin | Create a subject |
| `GET` | `/api/v1/subjects/` | Any | List subjects (paginated, filterable) |
| `GET` | `/api/v1/subjects/{id}` | Any | Get subject by ID |
| `PATCH` | `/api/v1/subjects/{id}` | Teacher/Admin | Update subject |
| `DELETE` | `/api/v1/subjects/{id}` | Teacher/Admin | Deactivate subject |

### Lesson Plan API

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/lesson-plans/` | Teacher/Admin | Create lesson plan |
| `GET` | `/api/v1/lesson-plans/` | Any | List plans (paginated, filterable) |
| `GET` | `/api/v1/lesson-plans/{id}` | Any | Get full plan with chapter tree |
| `PATCH` | `/api/v1/lesson-plans/{id}` | Teacher/Admin | Update plan metadata / status |
| `POST` | `/api/v1/lesson-plans/{id}/chapters` | Teacher/Admin | Add chapter |
| `POST` | `/api/v1/lesson-plans/{id}/chapters/{ch_id}/topics` | Teacher/Admin | Add topic |
| `POST` | `/api/v1/lesson-plans/{id}/chapters/{ch_id}/topics/{tp_id}/subtopics` | Teacher/Admin | Add subtopic |

### Topic Progress API

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/topic-progress/` | Teacher/Admin | Record or update topic completion |
| `PATCH` | `/api/v1/topic-progress/{id}` | Teacher/Admin | Partial update of a progress record |
| `GET` | `/api/v1/topic-progress/pending` | Any | Get pending topics for a plan |
| `GET` | `/api/v1/topic-progress/completion/{plan_id}` | Any | Completion statistics |
| `GET` | `/api/v1/topic-progress/faculty/{teacher_id}` | Any | Faculty progress summary |

### Enumeration Values

**Teaching Methods:** `theoretical` `practical` `ppt` `seminar` `lab` `assignment` `discussion` `case_study` `video_based`

**Topic Status:** `pending` `in_progress` `completed` `skipped`

**Understanding Level:** `excellent` `good` `average` `poor`

**Lesson Plan Status:** `draft` `active` `completed` `archived`

### Completion Stats Response Example

```json
{
  "success": true,
  "message": "Completion stats retrieved.",
  "data": {
    "lesson_plan_id": "683abc123def456789012345",
    "total_topics": 20,
    "completed_topics": 12,
    "in_progress_topics": 2,
    "pending_topics": 5,
    "skipped_topics": 1,
    "overall_completion_percentage": 60.0,
    "total_hours_planned": 40.0,
    "total_hours_delivered": 24.5
  }
}
```

---

## Roles

| Role | Permissions |
|---|---|
| `admin` | Full access to all endpoints |
| `teacher` | Manage own lesson plans; access subject and progress APIs |

---

## Error Response Format

```json
{
  "success": false,
  "error_code": "NOT_FOUND",
  "message": "Subject not found",
  "detail": null
}
```

| Code | HTTP Status | Meaning |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Bad email/password or expired token |
| `TOKEN_EXPIRED` | 401 | JWT has expired |
| `INSUFFICIENT_PERMISSIONS` | 403 | Wrong role for this endpoint |
| `NOT_FOUND` | 404 | Resource not found |
| `ALREADY_EXISTS` | 409 | Duplicate resource (e.g. subject code) |
| `VALIDATION_ERROR` | 422 | Request body failed Pydantic validation |
| `DATABASE_ERROR` | 500 | Unrecoverable database error |

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Academic Lesson Plan API` | Display name |
| `DEBUG` | `false` | Enables Swagger UI and verbose logging |
| `ENVIRONMENT` | `development` | Environment tag |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS allowed origins |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `lesson_plan_db` | Target database name |
| `JWT_SECRET_KEY` | -- | **Required** -- random secret for signing JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `BCRYPT_ROUNDS` | `12` | bcrypt work factor |

---

## Production Checklist

- Set `DEBUG=false`
- Set a strong, random `JWT_SECRET_KEY`
- Use a MongoDB Atlas URI with TLS enabled
- Restrict `ALLOWED_ORIGINS` to your actual frontend domain
- Run behind a reverse proxy (nginx / Traefik) with HTTPS termination
- Set `BCRYPT_ROUNDS` to at least `12`
- Enable MongoDB authentication