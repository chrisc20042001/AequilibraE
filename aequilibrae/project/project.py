import sqlite3
import os
import shutil
from aequilibrae.project.network import Network
from aequilibrae.parameters import Parameters
import warnings
from aequilibrae import logger
from aequilibrae.reference_files import spatialite_database
from .spatialite_connection import spatialite_connection
from .project_creation import initialize_tables


class Project:
    """AequilibraE project class

    ::

        from aequilibrae.project import Project

        existing = Project()
        existing.load('path/to/existing/project/folder')

        newfile = Project()
        newfile.new('path/to/new/project/folder')
        """
    environ_var = 'AEQUILIBRAE_PROJECT_PATH'

    def __init__(self):
        self.path_to_file: str = None
        self.source: str = None
        self.parameters = Parameters().parameters
        self.conn: sqlite3.Connection = None
        self.network: Network = None

    def open(self, project_path: str) -> None:
        """
        Loads project from disk

        Args:
            *project_path* (:obj:`str`): Full path to the project data folder. If the project inside does
            not exist, it will fail.
        """

        if self.__other_project_still_open():
            raise Exception('You already have a project open. Close that project before opening another one')

        file_name = os.path.join(project_path, 'project_database.sqlite')
        if not os.path.isfile(file_name):
            raise FileNotFoundError("Model does not exist. Check your path and try again")

        self.project_base_path = project_path
        self.path_to_file = file_name
        self.source = self.path_to_file
        self.conn = sqlite3.connect(self.path_to_file)
        self.conn = spatialite_connection(self.conn)
        self.__load_objects()
        logger.info(f'Opened project on {self.project_base_path}')

    def new(self, project_path: str) -> None:
        """Creates a new project

        Args:
            *project_path* (:obj:`str`): Full path to the project data folder. If folder exists, it will fail
        """
        if self.__other_project_still_open():
            raise Exception('You already have a project open. Close that project before creating a new one')

        self.project_base_path = project_path
        self.path_to_file = os.path.join(self.project_base_path, 'project_database.sqlite')
        self.source = self.path_to_file

        if os.path.isdir(project_path):
            raise FileNotFoundError("Location already exists. Choose a different name or remove the existing directory")
        self.__create_empty_project()
        self.__load_objects()
        logger.info(f'Created project on {self.project_base_path}')

    def close(self) -> None:
        """Safely closes the project"""
        if self.environ_var in os.environ:
            self.conn.close()
            os.environ.pop(self.environ_var, None)
            logger.info(f'Closed project on {self.project_base_path}')
        else:
            warnings.warn('There is no Aequilibrae project open that you may close')

    def load(self, project_path: str) -> None:
        """
        Loads project from disk

        Args:
            *project_path* (:obj:`str`): Full path to the project data folder. If the project inside does
            not exist, it will fail.
        """
        warnings.warn(f"Function has been deprecated. Use my_project.open({project_path}) instead", DeprecationWarning)
        self.open(project_path)

    def __load_objects(self):
        self.parameters = Parameters().parameters

        self.network = Network(self)
        os.environ[self.environ_var] = self.project_base_path

    def __create_empty_project(self):

        # We create the project folder and create the base file
        os.mkdir(self.project_base_path)
        shutil.copyfile(spatialite_database, self.path_to_file)
        self.conn = spatialite_connection(sqlite3.connect(self.path_to_file))

        # We create the enviroment variable with the the location for the project
        os.environ[self.environ_var] = self.project_base_path

        # Write parameters to the project folder
        p = Parameters()
        p.parameters["system"]["logging_directory"] = self.project_base_path
        p.write_back()

        # Create actual tables
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
        self.conn.commit()
        initialize_tables(self.conn)

    def __other_project_still_open(self) -> bool:
        if self.environ_var in os.environ:
            return True
        return False
