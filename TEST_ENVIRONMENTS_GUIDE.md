# Test Environments Guide

This project has **TWO SEPARATE** test environments for different purposes:

## 1. Main Test Environment (`/sql/`)

**Purpose**: General API testing, embeddings, multi-agent features

**Location**: `/sql/` directory with scripts:
- `01_extensions.sql` - PostgreSQL extensions
- `02_create_tables.sql` - Core tables
- `03_test_data.sql` - Test notes and data
- `04_embeddings.sql` - Embedding data
- `05_test_conversations.sql` - Conversation data

**Database**:
- Port: 5454
- Container: `youwoai_test_db`
- Database: `youwoai_test`
- User: postgres / 031203

**Features**:
- Note embeddings
- User conversations
- Multi-agent testing
- RAG testing

---

## 2. Humansa Test Environment (`/humansa_test_environment/`)

**Purpose**: Medical system testing with doctors, patients, appointments

**Location**: `/humansa_test_environment/` directory with:
```
humansa_test_environment/
├── README.md                      # Humansa-specific docs
├── docker-compose.yml             # Humansa Docker config
├── setup_humansa_test_db.sql     # Medical database schema
├── populate_humansa_test_data.py  # Medical test data
├── setup.sh                       # One-command setup
├── reset_data.sh                  # Quick data reset
└── cleanup.sh                     # Complete cleanup
```

**Database**:
- Port: 5456 (different from main)
- Container: `humansa_test_postgres`
- Database: `youwoai`
- User: youwo / youwo123

**Features**:
- 10 doctors with specialties
- 5 clinics across Singapore
- Patient medical records
- Appointment booking system
- Health packages
- Insurance providers

---

## Key Differences

| Feature | Main Test | Humansa Test |
|---------|-----------|--------------|
| **Port** | 5454 | 5456 |
| **Container** | youwoai_test_db | humansa_test_postgres |
| **Focus** | General API/ML | Medical System |
| **Tables** | notes, embeddings | doctors, patients, appointments |
| **Setup** | SQL scripts | Shell scripts |

## Usage

### Running Main Test Environment
```bash
# Assuming docker-compose.yml exists in root
docker-compose up -d
psql -h localhost -p 5454 -U postgres -d youwoai_test
```

### Running Humansa Test Environment
```bash
cd humansa_test_environment
./setup.sh                    # Complete setup
./reset_data.sh              # Reset data only
./cleanup.sh                 # Remove everything
```

### Running Both Simultaneously
```bash
# Main test
docker-compose up -d

# Humansa test
cd humansa_test_environment
./setup.sh

# Both run on different ports - no conflicts!
```

## When to Use Which?

**Use Main Test Environment for**:
- Testing embeddings and RAG
- Multi-agent conversations
- General API endpoints
- Note management features

**Use Humansa Test Environment for**:
- Medical consultation features
- Doctor search and booking
- Patient profile management
- Appointment workflows
- Healthcare-specific testing

## Important Notes

1. **Completely Isolated** - Different ports, containers, volumes
2. **No Shared Resources** - Each has its own schema
3. **Can Run Together** - No conflicts
4. **Different Credentials** - Check each environment's settings

This separation ensures clean testing environments for different features of the system.