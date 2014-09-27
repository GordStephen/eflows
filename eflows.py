import argparse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

parser = argparse.ArgumentParser(description='Loads, stores, and summarizes national energy flow data')

parser.add_argument('--load-data', help="Loads in national data from balance.txt and consumption.txt in current directory, saving it out to eflows.db", action="store_true")

args = parser.parse_args()

engine = create_engine('sqlite:///eflows.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Data Models

class Resource(Base):
    __tablename__ = 'resources'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "<Resource(name='%s')>" % (self.name)

if args.load_data:
    Base.metadata.create_all(engine)
    loading_session = Session()
    #TODO Read in balance.txt and consumption.txt, mapping to models 
    loading_session.close()

session = Session()
# Read values, generate plots, tables, etc
session.close()


