from sqlalchemy.orm import declarative_base  # Factory that builds the declarative Base class

Base = declarative_base()  # Subclass Base on every model so metadata.create_all() knows all tables
