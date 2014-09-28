import argparse, csv
import numpy as np
from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey
from sqlalchemy.schema import ForeignKeyConstraint 
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
        return "<Resource '%s'>" % (self.name)

class NodeCategoryClass(Base):
    __tablename__ = 'node_category_classes'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    #categories = relationship(NodeCategory, backref='class')

    def __repr__(self):
        return "<NodeCategoryClass '%s'>" % (self.name)

class NodeCategory(Base):
    __tablename__ = 'node_categories'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    class_id = Column(Integer, ForeignKey('node_category_classes.id'))
    #nodes = relationship(Node

    def __repr__(self):
        return "<NodeCategory '%s'>" % (self.name)

class Node(Base):
    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    category_id = Column(Integer, ForeignKey('node_categories.id'))

resource_source_nodes = Table(
    'resource_source_nodes', Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id')),
    Column('node_id', Integer, ForeignKey('nodes.id'))
)

resource_sink_nodes = Table(
    'resource_sink_nodes', Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id')),
    Column('node_id', Integer, ForeignKey('nodes.id'))
)

class Flow(Base):
    __tablename__ = 'flows'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    resource_id = Column(Integer, ForeignKey('resources.id'))
    source_node_id = Column(Integer) 
    sink_node_id = Column(Integer) 

    ForeignKeyConstraint(
        ['resource_id', 'source_node_id'], 
        ['resource_source_nodes.resource_id','resource_source_nodes.node_id']
    )

    ForeignKeyConstraint(
        ['resource_id', 'sink_node_id'], 
        ['resource_sink_nodes.resource_id','resource_sink_nodes.node_id']
    )

if args.load_data:
    Base.metadata.create_all(engine)
    loading_session = Session()

    # Load consumption.txt
    consumption = np.loadtxt(open('consumption.txt', 'rb'), delimiter='\t', dtype=str)

    # Remove useless rows
    consumption = consumption[np.where(np.in1d(consumption[:,0], ["b'ID'", "b'DESCRIPTION'", "b'UNIT'", "b'PARSETYPE'", "b'PRECISION'"], invert=True))]

    # Remove useless columns
    consumption = consumption[:, np.where(np.in1d(consumption[0,:], ["b'Millions of tonnes of oil equivalent'", "b'META'", "b'CODE'", "b''"], invert=True))[0]]

    # Remove redundant (summary) rows and their indicator columns
    cols_showing_redundant_rows = consumption[:, np.where(np.in1d(consumption[0,:], ["b'Total final consumption'", "b'SectorIn'"]))[0]]

    consumption = consumption[np.where(
        np.logical_not(np.logical_or(
            np.in1d(
                cols_showing_redundant_rows[:,0],
                ["b''", "b'Total final consumption'", "b'2012'"],
                invert=True
            ),
            np.in1d(
                cols_showing_redundant_rows[:,1],
                ["b''", "b'SectorIn'", "b'2012'"],
                invert=True
            )
        ))
    )[0]]

    consumption = consumption[:, np.where(np.in1d(consumption[0,:], ["b'Total final consumption'", "b'SectorIn'"], invert=True))[0]]

    # Consolidate top 2 rows into single useful row and trim top row
    consumption[1, np.where(consumption[0,:] != "b'Petajoules'")[0]] = consumption[0, np.where(consumption[0,:] != "b'Petajoules'")[0]]
    consumption = consumption[1:]

    # Move categorical data cols to start of row

    consumption_categories = np.concatenate((consumption[:,:1], consumption[:,-3:]), axis=1)
    consumption = consumption[:,1:-3]

    np.savetxt('consumption.csv', np.concatenate((consumption_categories, consumption), axis=1), delimiter=',', fmt='%s')

    #TODO Read in balance.txt and consumption.txt, mapping to models 
    loading_session.close()

session = Session()
# Read values, generate plots, tables, etc
session.close()


