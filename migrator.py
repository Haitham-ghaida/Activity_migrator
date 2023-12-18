import uuid
import bw2data as bd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


class ActivityProjectMigrator:
    """
    This class is meant to be used to migrate activities from one project to another.
    And between different versions of the ecoinvent database.
    It also handles the creation of activities and exchanges in the new database if they don't exist in it.
    The class caches the results of migration attempts to optimize performance.
    """

    def __init__(
        self,
        old_db_name: str,
        old_project_name: str,
        new_db_name: str,
        new_project_name: str,
    ) -> None:
        """
        Initializes the migrator with the specified old and new database and project names.

        Parameters:
        - old_db_name (str): Name of the old database.
        - old_project_name (str): Name of the old project.
        - new_db_name (str): Name of the new database.
        - new_project_name (str): Name of the new project.
        """
        self.old_db_name = old_db_name
        self.old_project_name = old_project_name
        self.new_db_name = new_db_name
        self.new_project_name = new_project_name
        self.cache = {}

    def migrate_activity(
        self,
        old_activity_code: str,
        return_code_only: bool = False,
        create_if_not_found: bool = False,
        return_key_only: bool = True,
        by_key: bool = False,
        biosphere_name: str = "biosphere3",
    ) -> tuple:
        """
        Migrates an activity from an one project to another. and between different versions of the ecoinvent database.
        If the activity doesn't exist in the new database, it can be created if specified.

        Parameters:
        ----------
        - old_activity_code (str): Code of the activity in the old database.
        - return_code_only (bool): If True, only the code of the migrated activity is returned.
        - create_if_not_found (bool): If True, the activity is created in the new database if it doesn't exist.
        - return_key_only (bool): If True, only the key of the migrated activity is returned.
        - by_key (bool): If True, the activity is searched for by key instead of by code.
        - biosphere_name (str): Name of the biosphere database.

        Returns:
        -------
        - tuple: A tuple containing the migrated activity and a boolean indicating whether the activity was created.
            - (activity, True) if the activity was created or found.
            - (activity, False) if the activity was not found.
            - (activity_code, True) if the activity was created or found and return_code_only is True.
            - (activity_code, False) if the activity was created or found and return_code_only is True.
            - (activity_key, True) if the activity was created or found and return_key_only is True.
            - (activity_key, False) if the activity was created or found and return_key_only is True.
        """
        # Check cache first
        if old_activity_code in self.cache:
            return self.cache[old_activity_code]

        # Set current project to old project and access the old database
        bd.projects.set_current(self.old_project_name)
        old_db = bd.Database(self.old_db_name)

        try:
            # Fetch the activity from the old database
            if by_key:
                activity = bd.get_activity(old_activity_code)
            else:
                activity = old_db.get(old_activity_code)
        except Exception as e:
            raise ValueError(
                f"Activity code '{old_activity_code}' doesn't exist in the old database '{self.old_db_name}'"
            ) from e

        # Prepare activity details for comparison
        activity_details = self._extract_activity_details(activity)

        # Switch to the new project and database
        bd.projects.set_current(self.new_project_name)
        new_db = bd.Database(self.new_db_name)

        # Search for a matching activity in the new database
        for new_activity in new_db:
            if all(
                new_activity[key] == value for key, value in activity_details.items()
            ):
                # return key if specified by or if return code only if specified otherwise return activity
                if return_key_only:
                    result = (new_activity.key, True)
                elif return_code_only:
                    result = (new_activity["code"], True)
                else:
                    result = (new_activity, True)
                self.cache[old_activity_code] = result
                return result

        # If no matching activity is found, create one if specified
        if create_if_not_found:
            return self.create_activity_if_not_found(old_activity_code)
        result = (activity, False)
        self.cache[old_activity_code] = result
        return result

    def _handle_biosphere_migration(
        self, activity_details, biosphere_name: str = "biosphere3"
    ):
        """
        Internal method.
        Handles the migration of biosphere activities.

        Parameters:
        ----------
        - activity_details (dict): A dictionary containing details of the biosphere activity.
        - biosphere_name (str): Name of the biosphere database.

        Returns:
        -------
        - tuple: A tuple containing the key of the migrated activity and a boolean indicating whether the activity was created.
            - (activity_key, True) if the activity was created or found.
            - (activity_key, False) if the activity was not found.
        """
        # Switch to the new project and database
        bd.projects.set_current(self.new_project_name)
        new_biosphere = bd.Database(biosphere_name)
        new_act = [
            act
            for act in new_biosphere
            if all(
                act.get(key) == value
                for key, value in activity_details.items()
                if value is not None
            )
        ]
        if len(new_act) == 1:
            new_act = new_act[0]
        else:
            # try to find a close match
            query = f"{activity_details['name']} {activity_details['categories']}"
            new_act = self._find_closest_match(query, new_biosphere)
            if new_act is None:
                raise ValueError(
                    f"Activity '{activity_details['name']}' not found in the new database '{self.new_db_name}'"
                )
            else:
                new_act = new_act[0]
        return (new_act.key, True)

    def _find_closest_match(self, query, database, score_cutoff=70):
        """
        Internal method.
        Finds the closest match to a query in a database using fuzzy matching.

        This is made to be used with the biosphere database.

        Parameters:
        ----------
        - query (str): The query to be matched.
        - database (Database object): The database to be searched.
        - score_cutoff (int): The minimum score for a match to be considered.

        Returns:
        -------
        - list: A list of matching entries.
        """
        # Pair each transformed entry with its original database entry
        choices = [
            (f"{entry['name']} {entry['categories']}", entry) for entry in database
        ]

        # Perform fuzzy matching using the transformed strings
        high_score_matches = process.extract(
            query,
            [choice[0] for choice in choices],
            scorer=fuzz.token_sort_ratio,
            limit=5,
        )

        # Filter out matches below the score cutoff and retrieve the original entries
        filtered_matches = [
            original
            for match, score in high_score_matches
            if score >= score_cutoff
            for transformed, original in choices
            if transformed == match
        ]

        return filtered_matches if filtered_matches else None

    def create_activity_if_not_found(
        self, old_activity_code: str, by_key: bool = False
    ) -> tuple:
        """
        Creates a new activity in the new database if it doesn't exist.
        Copies the details and exchanges from the old activity to the new one.

        Parameters:
        ----------
        - old_activity_code (str): Code of the activity in the old database.

        Returns:
        -------
        - tuple: A tuple containing the database and the code of the created activity i.e. the key.
        """
        # Attempt to migrate the activity first
        # migration_result = self.migrate_activity(old_activity_code, return_code_only=False)
        # if migration_result[1]:
        #     return migration_result[0]['code']

        # Fetch the activity from the old database
        bd.projects.set_current(self.old_project_name)
        old_db = bd.Database(self.old_db_name)

        if by_key:
            activity = bd.get_activity(old_activity_code)
        else:
            activity = old_db.get(old_activity_code)

        if activity is None:
            raise ValueError(
                f"Activity code '{old_activity_code}' doesn't exist in the old database '{self.old_db_name}'"
            )

        # Extract activity and exchange details
        activity_details = self._extract_activity_details(activity)
        exchange_details_list = self._collect_exchange_details(activity)

        # Generate a unique code for the new activity and create it in the new database
        unique_code = uuid.uuid4().hex
        bd.projects.set_current(self.new_project_name)
        new_db = bd.Database(self.new_db_name)
        new_act = new_db.new_activity(code=unique_code, **activity_details)
        new_act["auto_generated"] = True
        new_act.save()

        # Handle exchanges for the new activity
        self._handle_exchanges(new_act, exchange_details_list)

        return (new_act.key, True)

    def _extract_activity_details(self, activity: bd.Node) -> dict:
        """
        Internal method.
        Extracts essential details from an activity for comparison and migration.

        Parameters:
        - activity (Activity object): The activity from which details are to be extracted.

        Returns:
        - dict: A dictionary of activity details.
        """
        return {
            "name": activity.get("name"),
            "location": activity.get("location"),
            "unit": activity.get("unit"),
            "reference product": activity.get("reference product"),
        }

    def _collect_exchange_details(self, activity) -> list[dict]:
        """
        Internal method.
        Collects details of exchanges associated with an activity, stopping the collection
        when a duplicate exchange is detected.

        Parameters:
        - activity (Activity object): The activity from which exchanges are to be collected.

        Returns:
        - list of dicts: A list of dictionaries, each containing details of an exchange.
        """
        exchange_details_list = []
        seen_exchanges = set()

        for exc in activity.exchanges():
            exchange_key = (exc.input.key, exc.amount, exc.unit)
            if exchange_key in seen_exchanges:
                # TODO find a better way to deal with this,
                # i do this because sometimes it just loops forever
                # and i don't know why
                # maybe it's because of the way the exchanges are stored in the database
                # a possible solution is to use the exchange key as the key in the cache or
                # to use the exchange key as the key in the cache and the value as the activity code
                # the problem with this is that if for some reason there are duplicated exchanges on purpose
                # which means the creation process will miss some exchanges,
                # but for all the activities i've seen they have no duplicated exchanges so we are mostly safe.
                break  # Stop processing further exchanges if a duplicate is found
            seen_exchanges.add(exchange_key)
            # categories = target['categories']
            exchange_details = {
                "input": exc.input.key,
                "amount": exc.amount,
                "unit": exc.unit,
                "uncertainty_type": exc.uncertainty_type,
                "type": exc["type"],
                "loc": exc.get("loc"),
                "scale": exc.get("scale"),
                "negative": exc.get("negative"),
                "minimum": exc.get("minimum"),
                "maximum": exc.get("maximum"),
            }
            # So why do this and not put the name and the categories in the exchange details?
            # Because for some reason sometimes it does not let me access them from the exchange object
            # So i have to get the activity object from the db and get the name and categories from there
            # TODO look into why this happens and a better fix
            target = bd.get_activity(exc.input.key)
            name = target["name"]
            exchange_details.update({"name": name})
            if exchange_details["type"] == "biosphere":
                categories = target["categories"]
                exchange_details.update({"categories": categories})

            exchange_details_list.append(exchange_details)

        return exchange_details_list

    def _handle_exchanges(
        self,
        new_act: bd.Node,
        exchange_details_list: list[dict],
    ) -> None:
        """
        Internal method.
        Handles the creation of exchanges for a newly created activity in the new database.

        Parameters:
        ----------
        - new_act (Activity object): The newly created activity in the new database.
        - exchange_details_list (list of dicts): List of exchange details to be added to the new activity.

        Returns:
        -------
        - None
        """
        for exchange_details in exchange_details_list:
            if exchange_details["type"] == "biosphere":
                migrated_input = self._handle_biosphere_migration(exchange_details)
            elif exchange_details["type"] == "production":
                continue  # Skip production exchanges
            else:
                # Migrate the activity of each exchange
                migrated_input = self.migrate_activity(
                    exchange_details["input"], return_code_only=False, by_key=True
                )
                exchange_details["input"] = migrated_input[0]
            # if the exchange is not found in the new database
            if not migrated_input[1]:
                # create the activity of the exchange in the new database if it doesn't exist
                nested_technosphere_exchange = self.create_activity_if_not_found(
                    exchange_details["input"], by_key=True
                )
                # grab the key of the newly created activity
                exchange_details["input"] = nested_technosphere_exchange[0]

            # Add the exchange to the new activity
            new_act.new_exchange(**exchange_details).save()
