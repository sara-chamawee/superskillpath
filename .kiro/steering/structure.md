# Project Structure

```
.kiro/
  steering/         # AI assistant steering rules and project context
    product.md      # Product summary
    tech.md         # Tech stack, build commands
    structure.md    # This file — project organization
  specs/            # Feature specifications
src/
  __init__.py       # Main package
  models/           # Data models (Skill, Course, User, Chat, errors)
    __init__.py
  services/         # Business logic services
    __init__.py
  parsers/          # Seed data parsers
    __init__.py
tests/
  __init__.py       # Test package
seed-data/          # Seed data files
requirements.txt    # Python dependencies
```
