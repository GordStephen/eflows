import argparse, csv
import numpy as np
from eflows_load import load_consumption, load_balance
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, ForeignKey
from sqlalchemy.schema import ForeignKeyConstraint 
from sqlalchemy.orm import sessionmaker, relationship
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

    name = Column(String, primary_key=True)
    flows = relationship('Flow', backref='resource')

    def __repr__(self):
        return "<Resource '%s'>" % (self.name)

class NodeSector(Base):
    __tablename__ = 'node_sectors'

    name = Column(String, primary_key=True)
    nodes = relationship('Node', backref='sector')

    def __repr__(self):
        return "<NodeSector '%s'>" % (self.name)

class Node(Base):
    __tablename__ = 'nodes'

    name = Column(String, primary_key=True)
    sector_name = Column(String, ForeignKey('node_sectors.name'))
    source_resources = relationship('Resource', secondary='resource_sink_nodes', backref='source_nodes')
    sink_resources = relationship('Resource', secondary='resource_source_nodes', backref='sink_nodes')
    source_flows = relationship('Flow', foreign_keys='[Flow.source_node_name]', backref='source_node')
    sink_flows = relationship('Flow', foreign_keys='[Flow.sink_node_name]', backref='sink_node')

resource_source_nodes = Table(
    'resource_source_nodes', Base.metadata,
    Column('resource_name', String, ForeignKey('resources.name')),
    Column('node_name', String, ForeignKey('nodes.name'))
)

resource_sink_nodes = Table(
    'resource_sink_nodes', Base.metadata,
    Column('resource_name', String, ForeignKey('resources.name')),
    Column('node_name', String, ForeignKey('nodes.name'))
)

class Flow(Base):
    __tablename__ = 'flows'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    resource_name = Column(String, ForeignKey('resources.name'))
    source_node_name = Column(String, ForeignKey('nodes.name'))
    sink_node_name = Column(String, ForeignKey('nodes.name')) 
    year = Column(Integer)
    volume = Column(Float)

    ForeignKeyConstraint(
        ['resource_name', 'source_node_name'], 
        ['resource_source_nodes.resource_name','resource_source_nodes.node_name']
    )

    ForeignKeyConstraint(
        ['resource_name', 'sink_node_name'], 
        ['resource_sink_nodes.resource_name','resource_sink_nodes.node_name']
    )

if args.load_data:

    print('Clearing existing energy flows database...')
    Base.metadata.drop_all(engine)

    print('Building energy flows database schema...')
    Base.metadata.create_all(engine)
    loading_session = Session()

    # Load in raw data
    print('Reading in energy flows data...')
    balance = load_balance()
    consumption, consumption_categories = load_consumption()

    # Populate models from raw data
    print('Populating database from file...')

    # Create resources
    for resource in np.unique(balance[1:, np.where(balance[0] == 'Product')]):
        loading_session.add(Resource(name=resource))
    
    # Create consumption node sectors 
    for consumption_node_sector in np.unique(consumption_categories[1:, np.where(consumption_categories[0] == 'SectorOut')]):
        loading_session.add(NodeSector(name=consumption_node_sector))

    # Create basic nodes
    production = Node(name='Primary Production')
    imports = Node(name='Imports')
    loading_session.add_all([production, imports])

    annual_stock = Node(name='Annual (Short-Term) Stock')
    stocks = Node(name='Long-Term Stocks')
    stat_diff = Node(name='Statistical Differences')
    power = Node(name='Power Plants')
    refineries = Node(name='Refineries')
    other_conv = Node(name='Other Conversions')
    loading_session.add_all([annual_stock, stocks, stat_diff, power, refineries, other_conv])

    exports = Node(name='Exports')
    bunkers = Node(name='International Bunkers')
    power_loss = Node(name='Power Loss')
    loading_session.add_all([exports, bunkers, power_loss])

    # Create comsumption nodes 
    consumption_nodes = set(map(tuple, 
        consumption_categories[1:, np.where(
            np.in1d(consumption_categories[0], ['SectorOut', 'Consumption by sector'])
        )[0]]
    ))
    for sector, name in consumption_nodes:
        loading_session.add(Node(name=name, sector_name=sector))

    """
    # Add consumption flows to db
    for n in range(1,len(consumption)):
        
        for year_num in range(len(consumption[n])):
            new_flow = Flow(
                name = consumption_categories[n, 0],
                resource_name = consumption_categories[n, 1],
                source_node_name = 'Anuual (Short-Term) Stock',
                sink_node_name = consumption_categories[n, 3],
                volume = float(consumption[n, year_num]),
                year = int(consumption[0, year_num])
            )
            
    """

    loading_session.commit()
    loading_session.close()

session = Session()
# Read values, generate plots, tables, etc
session.close()


