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

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    flows = relationship('Flow', backref='resource')

    def __repr__(self):
        return "<Resource '%s'>" % (self.name)

class NodeCategoryClass(Base):
    __tablename__ = 'node_category_classes'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    categories = relationship('NodeCategory', backref='class_')

    def __repr__(self):
        return "<NodeCategoryClass '%s'>" % (self.name)

class NodeCategory(Base):
    __tablename__ = 'node_categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    class_id = Column(Integer, ForeignKey('node_category_classes.id'))
    nodes = relationship('Node', backref='category')

    def __repr__(self):
        return "<NodeCategory '%s'>" % (self.name)

class Node(Base):
    __tablename__ = 'nodes'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    category_id = Column(Integer, ForeignKey('node_categories.id'))
    source_resources = relationship('Resource', secondary='resource_sink_nodes', backref='source_nodes')
    sink_resources = relationship('Resource', secondary='resource_source_nodes', backref='sink_nodes')
    source_flows = relationship('Flow', foreign_keys='[Flow.source_node_id]', backref='source_node')
    sink_flows = relationship('Flow', foreign_keys='[Flow.sink_node_id]', backref='sink_node')

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
    name = Column(String, unique=True)
    resource_id = Column(Integer, ForeignKey('resources.id'))
    source_node_id = Column(Integer, ForeignKey('nodes.id'))
    sink_node_id = Column(Integer, ForeignKey('nodes.id')) 
    year = Column(Integer)
    volume = Column(Float)

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

    # Create basic nodes

    production = Node(name='Primary Production')
    imports = Node(name='Imports')

    annual_stock = Node(name='Annual (Short-Term) Stock')

    stocks = Node(name='Long-Term Stocks')
    stat_diff = Node(name='Statistical Differences')
    power = Node(name='Power Plants')
    refineries = Node(name='Refineries')
    other_conv = Node(name='Other Conversions')

    exports = Node(name='Exports')
    bunkers = Node(name='International Bunkers')
    power_loss = Node(name='Power Loss')
    
    consumption = load_consumption()
    balance = load_balance()

    """
    for n in range(1,len(consumption)):
        
        # Check if resource exists in db, add if not
        new_resource = Resource(name=consumption_categories[n,1])
        loading_session.add(new_resource)

        # Check if node category class exists in db, add if not
        new_node_category_class = NodeCategoryClass(name=consumption_categories[n,2])
        loading_session.add(new_node_category_class)

        # Check if node category exists in db, add if not
        new_node_category = NodeCategory(
            name=consumption_categories[n,3], 
            class_=new_node_category_class
        )
        loading_session.add(new_node_category)

        # Check if node exists in db, add if not
        new_node = Node(category=new_node_category)
        loading_session.add(new_node)

        # Add flows to db
        for year_num in range(len(consumption[n])):
            new_flow = Flow(
                name = consumption_categories[n,0],
                resource = new_resource,
                source_node = '',
                sink_node = '',
                volume = float(consumption[n, year_num]),
                year = int(consumption[0, year_num])
            )
            
    """


    loading_session.commit()
    loading_session.close()

session = Session()
# Read values, generate plots, tables, etc
session.close()


