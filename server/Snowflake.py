from snowflake.snowpark.functions import when_matched, when_not_matched
from snowflake.connector.pandas_tools import write_pandas
from snowflake.connector.pandas_tools import pd_writer
from snowflake.snowpark import *

import snowflake.connector
import pandas as pd 
import logging



class Snowpipe():
    '''
    This class enables communication with Snowflake using the Snowpark connector. Credentials need to be added to Snowflake.json in format seen below
    {
    "account"   : ""   ,
    "user"      : ""   ,
    "password"  : ""   ,
    "database"  : ""   ,
    "warehouse" : ""   ,
    "schema"    : ""   ,
    "role"      : ""
    }
    '''

    def __init__(self,connection_parameters):
        self.conntection_parameters = connection_parameters

    @property
    def snowpark_session(self):
        self.session = Session.builder.configs(self.conntection_parameters).create()
        return self.session

    @property
    def validate_conn(self):
        self.current_db = self.snowpark_session.get_current_database()
        return self.current_db

    def execute_query(self,query):
        self.query = query
        self.query_results = self.snowpark_session.sql(f"""{self.query}""")
        return self.query_results

    def get_pdf(self,pdf_query)->pd.DataFrame:
        self.pdf_query = pdf_query
        self.pdf_results = pd.DataFrame(self.execute_query(self.pdf_query).collect())
        return self.pdf_results
    


    #app_env = os.path.abspath(r'../env/app.env')
    #return load_dotenv(app_env)

