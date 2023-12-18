# ActivityProjectMigrator
## Overview

The ActivityProjectMigrator is a Python module designed for migrating activities between projects and different versions of the ecoinvent database in the Brightway framework. This tool is particularly useful when transitioning projects from older versions of ecoinvent to newer ones. It automates the process of finding equivalent activities in the new database and handles the creation of activities and their exchanges if they do not exist in the target database.
Features

- Migration between databases: Facilitates the migration of activities from one database to another, especially between different ecoinvent versions.
- Creation of missing activities: Automatically creates activities in the new database if they are not found.
- Performance optimization: Caches results of migration attempts to enhance performance.
- Flexible searching: Allows migration by either activity code or key.
- Biosphere handling: Special handling for migrating biosphere activities.

## Installation

To use ActivityProjectMigrator, ensure you have Python installed along with the bw2data and fuzzywuzzy packages. You can install these packages using pip:

```bash
pip install bw2data fuzzywuzzy
```

## Usage
First, import and initialize the ActivityProjectMigrator with your project and database names:

```python
from migrator import ActivityProjectMigrator

migrator = ActivityProjectMigrator(
    old_db_name="OLD_DB_NAME",
    old_project_name="OLD_PROJECT_NAME",
    new_db_name="NEW_DB_NAME",
    new_project_name="NEW_PROJECT_NAME"
)
```
### Migrating an Activity

To migrate an activity, use the migrate_activity method:

```python
activity_code = "ACTIVITY_CODE_OR_KEY"
result = migrator.migrate_activity(
    old_activity_code=activity_code,
    create_if_not_found=True
)
```
- `create_if_not_found=True` will create the activity in the new database if it's not found.
- Set `by_key=True` to search by activity key instead of code.

## Contributing

Contributions to the ActivityProjectMigrator are welcome! Please submit your pull requests or issues through the GitHub repository.

## License

This project is licensed under [BSD 3-Clause] - see the LICENSE file for details.
