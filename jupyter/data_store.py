import boto3
from botocore.exceptions import NoCredentialsError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from logger import setup_logger

logger = setup_logger('data_store', 'logs/data_store.log')

class DataStore:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        logger.debug("Initialized DataStore with database and S3 client")

    def save_to_db(self, data):
        """Save data to database"""
        session = self.Session()
        try:
            logger.debug(f"Saving data to database: {data}")
            # Assuming data is a dictionary and corresponding ORM models are defined
            # Example:
            # new_record = ResearchModel(**data)
            # session.add(new_record)
            session.commit()
            logger.info("Data saved to database successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving to database: {e}")
            raise
        finally:
            session.close()

    def backup_to_s3(self, file_path: str, object_name: str = None):
        if object_name is None:
            object_name = file_path.split('/')[-1]
        try:
            self.s3_client.upload_file(file_path, Config.S3_BUCKET_NAME, object_name)
            logger.info(f"Backup {file_path} to S3 bucket {Config.S3_BUCKET_NAME} as {object_name}.")
        except FileNotFoundError:
            logger.error("The file was not found.")
        except NoCredentialsError:
            logger.critical("S3 credentials not available.")
from botocore.exceptions import NoCredentialsError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from logger import setup_logger

logger = setup_logger('data_store', 'logs/data_store.log')

class DataStore:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )

    def save_to_db(self, data):
        """Save data to database"""
        session = self.Session()
        try:
            # Assuming data is a dictionary and corresponding ORM models are defined
            # Example:
            # new_record = ResearchModel(**data)
            # session.add(new_record)
            session.commit()
            logger.info("Data saved to database successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving to database: {e}")
            raise
        finally:
            session.close()

    def backup_to_s3(self, file_path: str, object_name: str = None):
        """Backup file to S3"""
        if object_name is None:
            object_name = file_path.split('/')[-1]
        try:
            self.s3_client.upload_file(file_path, Config.S3_BUCKET_NAME, object_name)
            logger.info(f"Backup {file_path} to S3 bucket {Config.S3_BUCKET_NAME} as {object_name}.")
        except FileNotFoundError:
            logger.error("The file was not found.")
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except NoCredentialsError:
            logger.critical("S3 credentials not available.")
