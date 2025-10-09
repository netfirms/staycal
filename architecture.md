### High-Level Architecture Diagram

This diagram illustrates the overall structure of the application, showing the main components and how they interact.

```mermaid
flowchart LR
  subgraph Client
    A[Browser\nHTML + CSS + HTMX + FullCalendar]
  end
  
  subgraph Railway[Railway Deployment]
    subgraph App[FastAPI Monolith]
      B[FastAPI Routers\n- public_views\n- auth_views\n- app_views\n- rooms_views\n- bookings_views\n- homestays_views\n- calendar_htmx_views\n- admin_views]
      C[Jinja2 Templates\nSSR + HTMX partials]
      D["Security Middleware\n (Session cookie)"]
      E[SQLAlchemy ORM]
      G[Auto-Checkout Service]
    end
    
    F[(PostgreSQL / SQLite)]
  end
  
  A -- "HTTP Request (GET/POST)" --> D
  D -- Authenticated Request --> B
  B -- Render --> C
  B -- Query/Commit --> E
  E -- Connection --> F
  B -- trigger --> G
  B -- "SSE (Server-Sent Events)" --> A
```

### Low-Level Architecture (Data Model) Diagram

This Entity-Relationship (ER) diagram provides a detailed look at the database schema, including the tables, their fields, and the relationships between them.

```mermaid
erDiagram
  USERS ||--o{ HOMESTAYS : owns
  USERS ||--o{ SUBSCRIPTIONS : has
  HOMESTAYS ||--o{ ROOMS : contains
  HOMESTAYS ||--o{ USERS : staff_of
  ROOMS ||--o{ BOOKINGS : has

  USERS {
    id int PK
    email varchar
    hashed_password varchar
    role varchar
    homestay_id int
    created_at timestamp
  }
  SUBSCRIPTIONS {
    id int PK
    owner_id int
    plan_name enum
    status enum
    expires_at timestamp
  }
  HOMESTAYS {
    id int PK
    owner_id int
    name varchar
    address varchar
    created_at timestamp
  }
  ROOMS {
    id int PK
    homestay_id int
    name varchar
    capacity int
    default_rate decimal
  }
  BOOKINGS {
    id int PK
    room_id int
    guest_name varchar
    guest_contact varchar
    start_date date
    end_date date
    price decimal
    status enum
    created_by int FK
  }
```
