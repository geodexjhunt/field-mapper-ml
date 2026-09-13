# Field Mapper ML

A Python application that leverages semantic similarity and machine learning to assist with field mapping during data migration.

## Overview

Field Mapper ML helps automate the process of matching source database fields to target database fields using embeddings and semantic similarity scoring. It supports two matching strategies:

1. **Legacy-backed Matches**: Match against previously approved/verified field mappings (higher confidence)
2. **Direct Semantic Matches**: Match directly against all available target fields, even without prior approval (separate confidence scoring)

## Features

- 🔄 **Dual Matching Strategy**: Leverages both historical mappings and direct target field catalog
- 📊 **Confidence Scoring**: Distinguishes between legacy-backed and direct semantic matches
- 🤖 **Flexible ML Backend**: Easy switch between cloud APIs (Google, Cohere) and local models (Sentence Transformers)
- 🔒 **Privacy-First**: Field names only—no sensitive data exposure
- 📝 **Batch Processing**: Review multiple files (~100-200 fields) per job
- ✅ **Approval Workflow**: User review and approval/rejection of proposed mappings
- 🗄️ **Extensible Data Loaders**: Load source/target metadata from SQL and approved mappings from JSON/CSV

## Architecture

```
Source Fields (metadata)
    ↓
Embedding Generator (API or Local)
    ↓
Dual-Source Scoring:
  1. Legacy Approved Mappings (high confidence)
  2. Direct Target Field Catalog (separate confidence)
    ↓
Ranked Proposals + Confidence Scores
    ↓
User Review/Approval UI
```

## Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
git clone https://github.com/geodexjhunt/field-mapper-ml.git
cd field-mapper-ml
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Choose backend: 'google', 'cohere', or 'local'
EMBEDDING_BACKEND=local

# If using cloud API
GOOGLE_API_KEY=your_key_here
COHERE_API_KEY=your_key_here
```

### Basic Usage

```python
from field_mapper.mapper import FieldMapper
from field_mapper.models import SourceField, TargetField

# Initialize mapper
mapper = FieldMapper(backend='local')  # or 'google', 'cohere'

# Load your data
approved_mappings = [...]  # List of historical approved mappings
target_fields = [...]      # All available target fields

mapper.load_catalog(approved_mappings, target_fields)

# Source fields to map
source_fields = [
    SourceField(name='customer_id', table='customers', data_type='INTEGER'),
    SourceField(name='email_addr', table='customers', data_type='VARCHAR(255)'),
    # ...
]

# Get mapping proposals
proposals = mapper.find_matches(source_fields)

# Review proposals
for proposal in proposals:
    print(f"Source: {proposal.source_field}")
    print(f"  Legacy Matches: {proposal.legacy_matches}")
    print(f"  Direct Matches: {proposal.direct_matches}")
```

## Project Structure

```
field-mapper-ml/
├── field_mapper/
│   ├── __init__.py
│   ├── mapper.py              # Main field mapper logic
│   ├── loaders/               # SQL and mapping file loaders
│   ├── embeddings.py          # Embedding backends (Google, Cohere, Local)
│   ├── scoring.py             # Similarity scoring logic
│   ├── models.py              # Data models
│   └── utils.py               # Utility functions
├── examples/
│   ├── load_from_sql_example.py
│   ├── load_mappings_example.py
│   ├── sample_approved_mappings.json
│   ├── sample_target_fields.json
│   ├── sample_source_fields.json
│   └── run_example.py
├── tests/
│   └── test_mapper.py
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration & Backends

### Local Model (Recommended for Privacy)
- Uses `sentence-transformers` with MiniLM model (~60MB)
- Completely offline, no API calls
- Best for security-conscious deployments

### Google Embeddings API
- Free tier: 1,500 requests/day
- No credit card required
- Excellent quality

### Cohere Embed
- Free tier: 1 million tokens/month
- Multilingual support
- Great for scaling

## Confidence Scoring

The system returns two types of matches:

### Legacy-backed Matches
- Matched against previously approved mappings
- Higher confidence baseline (matched against proven mappings)
- Includes metadata from the approved mapping

### Direct Semantic Matches
- Matched directly against all target fields
- Separate confidence score to distinguish from legacy
- Useful for discovering new mappings not in historical data

Each match includes:
- `target_field`: The proposed target field name
- `target_table`: The target table name
- `confidence_score`: Similarity score (0.0 to 1.0)
- `match_type`: 'legacy' or 'direct'
- `supporting_metadata`: Source field constraints, data types, etc.

## API Usage

### REST Endpoint Example

```bash
curl -X POST http://localhost:5000/api/map \
  -H "Content-Type: application/json" \
  -d '{
    "source_fields": [
      {"name": "customer_id", "table": "users", "data_type": "INT"},
      {"name": "full_name", "table": "users", "data_type": "VARCHAR"}
    ]
  }'
```

Response:
```json
{
  "proposals": [
    {
      "source_field": "customer_id",
      "legacy_matches": [
        {
          "target_field": "cust_id",
          "target_table": "dim_customer",
          "confidence_score": 0.92,
          "match_type": "legacy"
        }
      ],
      "direct_matches": [
        {
          "target_field": "customer_id_new",
          "target_table": "customers",
          "confidence_score": 0.87,
          "match_type": "direct"
        }
      ]
    }
  ]
}
```

## Data Loaders

### Load field metadata from Microsoft SQL Server

```python
from field_mapper.loaders import MSSQLLoader

loader = MSSQLLoader(
    server="localhost",
    database="FieldMapperDemo",
    trusted_connection=True,
)

source_fields = loader.load_source_fields(
    schema="dbo",
    table="customers",
    include_min_max=True,
    include_unique_counts=True,
)
target_fields = loader.load_target_fields(schema="dw", table="dim_customer")
```

The SQL loader is structured so other database loaders can follow the same
`extract_field_metadata`, `load_source_fields`, and `load_target_fields`
pattern later.

### Load approved mappings from JSON or CSV

```python
from field_mapper.loaders import ApprovedMappingLoader

loader = ApprovedMappingLoader()
approved_mappings = loader.load("approved_mappings.json")
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running Examples

```bash
python examples/run_example.py
```

## Future Enhancements

- [ ] Web UI for approval/rejection workflow
- [ ] Learning from user rejections to improve scoring
- [ ] Support for constraint-based matching (length, range, etc.)
- [ ] Batch job history and audit trail
- [ ] Integration with common migration tools (AWS DMS, Talend, etc.)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
